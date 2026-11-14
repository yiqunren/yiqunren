"""Claude（API）轉接器（SPEC NFR-7）：後端直接用 Anthropic 官方 Python SDK 呼叫 Messages API，只做對話。

- 認證：只用啟動後端的環境裡的 ANTHROPIC_API_KEY；這裡只檢查有沒有設定，不讀出、不存、不記錄。
- 前文：TurnInput.history（同一段對話先前完成的回合）依序帶給模型，再加上這次的訊息。
- 花費上限（FR-1）：送出前用 count_tokens 取得輸入 token 數，依 PRICES 算出輸入花費（以快取寫入價計），
  再用剩下的預算換算這次最多能輸出的 token 數（含思考），當成 max_tokens。
  同一段對話上一個完成回合的請求在 4 分鐘內開始、設定沒變時，假設它已進快取的部分會命中、按快取讀取價估算，
  讓長對話撐更久；但輸出上限同時保證就算快取沒命中，單回合花費也不超過上限的 2 倍（NFR-7）。
- 思考（FR-2）：支援 adaptive thinking 的模型一律開啟。串流時依內容區塊類型回報「思考中」「回答中」，
  並把各思考區塊從開始到結束的時間加總，回合完成時和回覆一起存下。思考內容不要求回傳、也不存。
- 失敗只記固定分類（classify）；錯誤訊息原文不存、不顯示，log 只記分類與請求 ID。
- 中斷：取消進行中的請求，請求結束後丟 Interrupted。伺服器重啟時請求隨舊程序結束：
  這裡不呼叫 hooks.began，回合服務會把留下的回合標為未知。
"""
from __future__ import annotations

import asyncio
import logging
import math
import os
import time

import anthropic

from app.storage import turns
from app.web.config import ConfigError
from app.web.runner import Failed, Hooks, Interrupted, Runner, TurnInput


logger = logging.getLogger(__name__)

CODE = 'claude_api'
KEY_ENV = 'ANTHROPIC_API_KEY'
DEFAULT_MODEL = 'claude-opus-5-5'
MAX_OUTPUT = 64_000  # 串流請求的輸出上限（token）
MIN_OUTPUT = 1_024  # 依預算換算後能輸出的量少於這個數，就不送出
CACHE_WRITE_FACTOR = 1.25  # 5 分鐘快取寫入的價格倍數；沒假設命中快取的輸入一律以此估最高值
CACHE_READ_FACTOR = 0.1  # 快取讀取的價格倍數（部分模型更便宜，這裡取較高的 0.1 倍估算）
CACHE_FRESH_SECONDS = 240  # 快取保留 5 分鐘（從請求開始算）；上次請求開始後 4 分鐘內才假設命中
WORST_CASE_FACTOR = 2  # 假設命中快取時，就算沒命中，單回合花費也不超過上限的這個倍數

# 每百萬 token 的美元價格（輸入, 輸出），照 Anthropic 官方價格頁維護（2026-11-03 的價格）。
PRICES = {
    'claude-fable-5-2': (8.0, 40.0),
    'claude-fable-5-1': (10.0, 50.0),
    'claude-fable-5': (10.0, 50.0),
    'claude-opus-5-5': (4.0, 20.0),
    'claude-opus-5': (5.0, 25.0),
    'claude-opus-4-8': (5.0, 25.0),
    'claude-opus-4-7': (5.0, 25.0),
    'claude-opus-4-6': (5.0, 25.0),
    'claude-sonnet-5-5': (2.0, 10.0),
    'claude-sonnet-5': (2.0, 10.0),
    'claude-sonnet-4-6': (3.0, 15.0),
    'claude-haiku-5-5': (0.10, 0.50),
    'claude-haiku-4-5': (1.0, 5.0),
}
# Claude Haiku 5.5 的輸入超過 100K token 時改用較高的價格。
TIERED = {'claude-haiku-5-5': (100_000, (0.50, 2.50))}
# 價格表裡不支援 adaptive thinking 的模型；不在價格表裡的模型也不送思考設定（不知道支不支援）。
NO_ADAPTIVE_THINKING = frozenset({'claude-haiku-4-5'})

THINKING_BLOCKS = frozenset({'thinking', 'redacted_thinking'})
THINKING, ANSWERING = 'thinking', 'answering'  # 進度裡的階段（FR-2）

CREDIT_TOO_LOW = 'credit balance is too low'  # API 以 400 回報帳戶額度不足時的訊息（官方 CLI 也這樣判斷）
PROMPT_TOO_LONG = 'prompt is too long'  # 輸入超過模型能讀的長度時，API 以 400 回報的訊息（官方文件 context windows）


def prices(model: str, input_tokens: int) -> tuple[float, float] | None:
    """(輸入, 輸出) 每百萬 token 的美元價格；不在價格表裡回傳 None。"""
    tier = TIERED.get(model)
    if tier is not None and input_tokens > tier[0]:
        return tier[1]
    return PRICES.get(model)


def output_limit(budget: float, model: str, input_tokens: int, cached_tokens: int = 0) -> int | None:
    """依預算換算這次最多能輸出的 token 數；模型不在價格表裡時回傳 None。

    cached_tokens 是假設會命中快取的輸入 token 數（0 表示不假設）。有假設時，命中部分按快取讀取價估算，
    但同時要求整段輸入都沒命中時，花費仍不超過上限的 WORST_CASE_FACTOR 倍（SPEC NFR-7）。"""
    found = prices(model, input_tokens)
    if found is None:
        return None
    price_in, price_out = found
    worst = input_tokens * price_in * CACHE_WRITE_FACTOR / 1_000_000
    remaining = budget - worst
    cached = min(max(cached_tokens, 0), input_tokens)
    if cached:
        expected = (cached * CACHE_READ_FACTOR + (input_tokens - cached) * CACHE_WRITE_FACTOR) * price_in / 1_000_000
        remaining = min(budget - expected, WORST_CASE_FACTOR * budget - worst)
    if remaining <= 0:
        return 0
    return math.floor(remaining * 1_000_000 / price_out)


def classify(exc: Exception) -> str:
    """SDK 例外 → 固定分類（FR-2）。只看例外型別、狀態碼與錯誤類型。"""
    if isinstance(exc, (anthropic.AuthenticationError, anthropic.PermissionDeniedError)):
        return turns.AUTH_FAILED
    if isinstance(exc, anthropic.NotFoundError):
        return turns.MODEL_UNAVAILABLE
    if isinstance(exc, anthropic.RateLimitError):
        return turns.SERVICE_BUSY
    if isinstance(exc, anthropic.APIStatusError):
        if exc.status_code == 402 or exc.type == 'billing_error':
            return turns.QUOTA_EXCEEDED
        message = str(exc.api_message or '').lower()
        if exc.status_code == 400 and CREDIT_TOO_LOW in message:
            return turns.QUOTA_EXCEEDED
        if exc.status_code == 413 or (exc.status_code == 400 and PROMPT_TOO_LONG in message):
            return turns.CONVERSATION_TOO_LONG
        if exc.status_code >= 500:
            return turns.SERVICE_BUSY
        return turns.INTERNAL_ERROR
    if isinstance(exc, anthropic.APIConnectionError):  # 含連線逾時
        return turns.SERVICE_BUSY
    return turns.INTERNAL_ERROR


def adaptive_thinking(model: str) -> bool:
    return model in PRICES and model not in NO_ADAPTIVE_THINKING


async def follow(stream, progress, clock) -> tuple[object, float | None]:
    """讀完串流：階段改變時回報進度，加總思考區塊的時間。回傳 (完整訊息, 思考秒數或 None)。"""
    phase = None
    opened: dict[int, float] = {}  # 進行中的思考區塊：區塊編號 → 開始時間
    spent, thought = 0.0, False
    async for event in stream:
        if event.type == 'content_block_start':
            kind = event.content_block.type
            current = THINKING if kind in THINKING_BLOCKS else ANSWERING if kind == 'text' else None
            if kind in THINKING_BLOCKS:
                opened[event.index] = clock()
            if current is not None and current != phase:
                phase = current
                progress({'kind': 'phase', 'phase': current})
        elif event.type == 'content_block_stop' and event.index in opened:
            spent += clock() - opened.pop(event.index)
            thought = True
    message = await stream.get_final_message()
    return message, (round(max(spent, 0.0), 1) if thought else None)


def messages_for(turn: TurnInput) -> list[dict]:
    found = []
    for message, reply in turn.history:
        found.append({'role': 'user', 'content': message})
        found.append({'role': 'assistant', 'content': reply})
    found.append({'role': 'user', 'content': turn.message})
    return found


class ClaudeApiRunner(Runner):
    """client：anthropic.AsyncAnthropic（測試時換成假的）；clock 量思考時間用、cache_clock 判斷快取是否還在
    （兩者測試時都可換掉）。"""

    def __init__(self, client, clock=time.monotonic, cache_clock=time.monotonic):
        self.client = client
        self.clock = clock
        self.cache_clock = cache_clock
        self._tasks: dict[str, asyncio.Task] = {}
        self._stopping: set[str] = set()  # 擁有者要求中斷的回合（可能在 run 開始之前就送到）
        # 每段對話上一個完成回合的快取線索：(請求設定, 已進快取的 token 數, 請求開始時間)。只放記憶體，重啟就沒了。
        self._cache: dict[str, tuple[tuple, int, float]] = {}

    async def run(self, turn: TurnInput, hooks: Hooks) -> None:
        if turn.turn_id in self._stopping:
            self._stopping.discard(turn.turn_id)
            raise Interrupted()  # 還沒送出任何請求
        task = asyncio.create_task(self._reply(turn, hooks.progress))
        self._tasks[turn.turn_id] = task
        try:
            try:
                done, _ = await asyncio.wait({task}, timeout=turn.timeout)
            except asyncio.CancelledError:
                # 伺服器關閉：請求無法跨程序保留，一併取消；回合由下次啟動標為未知。
                task.cancel()
                await asyncio.wait({task})
                raise
            if not done:
                task.cancel()
                await asyncio.wait({task})
                raise Failed(turns.TIMEOUT)
            if task.cancelled():
                raise Interrupted()  # stop 取消了請求，請求已經結束
            reply, thinking_seconds, hint = task.result()  # Failed 或其他例外照原樣往外傳
        finally:
            self._tasks.pop(turn.turn_id, None)
            self._stopping.discard(turn.turn_id)
        hooks.save(reply, thinking_seconds=thinking_seconds)
        self._remember(turn.conversation_id, hint)  # 只有完成的回合會成為下次的前文，失敗的不記

    def _remember(self, conversation_id: str, hint: tuple[tuple, int, float]) -> None:
        now = self.cache_clock()
        for key in [key for key, (_, _, started) in self._cache.items() if now - started >= CACHE_FRESH_SECONDS]:
            del self._cache[key]  # 過期的線索用不到了
        if hint[1] > 0:
            self._cache[conversation_id] = hint
        else:
            self._cache.pop(conversation_id, None)

    def _cached_tokens(self, conversation_id: str, settings: tuple) -> int:
        """上一個完成回合 4 分鐘內開始、設定沒變時，回傳它已進快取的 token 數；否則 0（SPEC NFR-7）。"""
        found = self._cache.get(conversation_id)
        if found is None:
            return 0
        previous, tokens, started = found
        if previous != settings or self.cache_clock() - started >= CACHE_FRESH_SECONDS:
            return 0
        return tokens

    async def stop(self, turn_id: str) -> None:
        self._stopping.add(turn_id)
        task = self._tasks.get(turn_id)
        if task is not None:
            task.cancel()

    async def _reply(self, turn: TurnInput, progress) -> tuple[str, float | None, tuple[tuple, int, float]]:
        """回傳（回覆文字, 思考秒數, 快取線索）。"""
        model = turn.model or DEFAULT_MODEL
        params: dict = {'model': model, 'messages': messages_for(turn), 'cache_control': {'type': 'ephemeral'}}
        if adaptive_thinking(model):
            params['thinking'] = {'type': 'adaptive'}
        if turn.effort:
            params['output_config'] = {'effort': turn.effort}
        settings = (model, turn.effort, 'thinking' in params)  # 任一項改變，前文的快取就失效
        limit, capped = MAX_OUTPUT, False
        try:
            if turn.budget is not None:
                if prices(model, 0) is None:
                    raise Failed(turns.MODEL_UNAVAILABLE)  # 沒有價格就算不出花費，不送出
                counted = await self.client.messages.count_tokens(**params)
                cached = self._cached_tokens(turn.conversation_id, settings)
                allowed = output_limit(turn.budget, model, counted.input_tokens, cached)
                if allowed is None:
                    raise Failed(turns.MODEL_UNAVAILABLE)
                if allowed < MIN_OUTPUT:
                    # 上限本身夠輸出、卻被前文吃掉：開新對話就能繼續，所以記為對話太長（FR-2）。
                    too_long = bool(turn.history) and output_limit(turn.budget, model, 0) >= MIN_OUTPUT
                    raise Failed(turns.CONVERSATION_TOO_LONG if too_long else turns.BUDGET_EXCEEDED)
                if allowed < MAX_OUTPUT:
                    limit, capped = allowed, True
            started = self.cache_clock()  # 快取保留時間從請求開始算
            async with self.client.messages.stream(max_tokens=limit, **params) as stream:
                message, thinking_seconds = await follow(stream, progress, self.clock)
        except anthropic.APIError as exc:
            kind = classify(exc)
            logger.warning('Claude API 回合 %s 失敗：%s（請求 ID：%s）', turn.turn_id, kind,
                           getattr(exc, 'request_id', None) or '無')
            raise Failed(kind) from None
        if message.stop_reason == 'refusal':
            raise Failed(turns.REFUSED)
        if message.stop_reason == 'max_tokens':
            raise Failed(turns.BUDGET_EXCEEDED if capped else turns.REPLY_TOO_LONG)
        if message.stop_reason == 'model_context_window_exceeded':
            raise Failed(turns.CONVERSATION_TOO_LONG)  # 回覆寫到一半撞到模型長度上限，截斷的內容不存
        text = ''.join(block.text for block in message.content if block.type == 'text')
        if not text.strip():
            raise Failed(turns.INTERNAL_ERROR)
        usage = getattr(message, 'usage', None)
        stored = (getattr(usage, 'cache_creation_input_tokens', None) or 0) + \
            (getattr(usage, 'cache_read_input_tokens', None) or 0)
        return text, thinking_seconds, (settings, stored, started)


def build() -> ClaudeApiRunner:
    """後端啟動時建立；沒設定 ANTHROPIC_API_KEY 就拒絕啟動（只檢查有沒有值）。"""
    if not os.environ.get(KEY_ENV):
        raise ConfigError('要接上 Claude（API）必須在啟動後端的環境裡設定 %s' % KEY_ENV)
    return ClaudeApiRunner(anthropic.AsyncAnthropic())
