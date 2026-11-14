"""Claude（API）轉接器（SPEC NFR-7）：後端直接用 Anthropic 官方 Python SDK 呼叫 Messages API，只做對話。

- 認證：只用啟動後端的環境裡的 ANTHROPIC_API_KEY；這裡只檢查有沒有設定，不讀出、不存、不記錄。
- 前文：TurnInput.history（同一段對話先前完成的回合）依序帶給模型，再加上這次的訊息。
- 花費上限（FR-1）：送出前用 count_tokens 取得輸入 token 數，依 PRICES 算出輸入花費（以快取寫入價計），
  再用剩下的預算換算這次最多能輸出的 token 數（含思考），當成 max_tokens。單回合因此不會超過上限。
- 失敗只記固定分類（classify）；錯誤訊息原文不存、不顯示，log 只記分類與請求 ID。
- 中斷：取消進行中的請求，請求結束後丟 Interrupted。伺服器重啟時請求隨舊程序結束：
  這裡不呼叫 hooks.began，回合服務會把留下的回合標為未知。
"""
from __future__ import annotations

import asyncio
import logging
import math
import os

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
CACHE_WRITE_FACTOR = 1.25  # 5 分鐘快取寫入的價格倍數；輸入花費一律以此估最高值

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

CREDIT_TOO_LOW = 'credit balance is too low'  # API 以 400 回報帳戶額度不足時的訊息（官方 CLI 也這樣判斷）


def prices(model: str, input_tokens: int) -> tuple[float, float] | None:
    """(輸入, 輸出) 每百萬 token 的美元價格；不在價格表裡回傳 None。"""
    tier = TIERED.get(model)
    if tier is not None and input_tokens > tier[0]:
        return tier[1]
    return PRICES.get(model)


def output_limit(budget: float, model: str, input_tokens: int) -> int | None:
    """依預算換算這次最多能輸出的 token 數；模型不在價格表裡時回傳 None。"""
    found = prices(model, input_tokens)
    if found is None:
        return None
    price_in, price_out = found
    remaining = budget - input_tokens * price_in * CACHE_WRITE_FACTOR / 1_000_000
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
        if exc.status_code == 400 and CREDIT_TOO_LOW in str(exc.api_message or '').lower():
            return turns.QUOTA_EXCEEDED
        if exc.status_code >= 500:
            return turns.SERVICE_BUSY
        return turns.INTERNAL_ERROR
    if isinstance(exc, anthropic.APIConnectionError):  # 含連線逾時
        return turns.SERVICE_BUSY
    return turns.INTERNAL_ERROR


def messages_for(turn: TurnInput) -> list[dict]:
    found = []
    for message, reply in turn.history:
        found.append({'role': 'user', 'content': message})
        found.append({'role': 'assistant', 'content': reply})
    found.append({'role': 'user', 'content': turn.message})
    return found


class ClaudeApiRunner(Runner):
    """client：anthropic.AsyncAnthropic（測試時換成假的）。"""

    def __init__(self, client):
        self.client = client
        self._tasks: dict[str, asyncio.Task] = {}
        self._stopping: set[str] = set()  # 擁有者要求中斷的回合（可能在 run 開始之前就送到）

    async def run(self, turn: TurnInput, hooks: Hooks) -> None:
        if turn.turn_id in self._stopping:
            self._stopping.discard(turn.turn_id)
            raise Interrupted()  # 還沒送出任何請求
        task = asyncio.create_task(self._reply(turn))
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
            reply = task.result()  # Failed 或其他例外照原樣往外傳
        finally:
            self._tasks.pop(turn.turn_id, None)
            self._stopping.discard(turn.turn_id)
        hooks.save(reply)

    async def stop(self, turn_id: str) -> None:
        self._stopping.add(turn_id)
        task = self._tasks.get(turn_id)
        if task is not None:
            task.cancel()

    async def _reply(self, turn: TurnInput) -> str:
        model = turn.model or DEFAULT_MODEL
        params: dict = {'model': model, 'messages': messages_for(turn), 'cache_control': {'type': 'ephemeral'}}
        if turn.effort:
            params['output_config'] = {'effort': turn.effort}
        limit, capped = MAX_OUTPUT, False
        try:
            if turn.budget is not None:
                if prices(model, 0) is None:
                    raise Failed(turns.MODEL_UNAVAILABLE)  # 沒有價格就算不出花費，不送出
                counted = await self.client.messages.count_tokens(**params)
                allowed = output_limit(turn.budget, model, counted.input_tokens)
                if allowed is None:
                    raise Failed(turns.MODEL_UNAVAILABLE)
                if allowed < MIN_OUTPUT:
                    raise Failed(turns.BUDGET_EXCEEDED)
                if allowed < MAX_OUTPUT:
                    limit, capped = allowed, True
            async with self.client.messages.stream(max_tokens=limit, **params) as stream:
                message = await stream.get_final_message()
        except anthropic.APIError as exc:
            kind = classify(exc)
            logger.warning('Claude API 回合 %s 失敗：%s（請求 ID：%s）', turn.turn_id, kind,
                           getattr(exc, 'request_id', None) or '無')
            raise Failed(kind) from None
        if message.stop_reason == 'refusal':
            raise Failed(turns.REFUSED)
        if message.stop_reason == 'max_tokens':
            raise Failed(turns.BUDGET_EXCEEDED if capped else turns.REPLY_TOO_LONG)
        text = ''.join(block.text for block in message.content if block.type == 'text')
        if not text.strip():
            raise Failed(turns.INTERNAL_ERROR)
        return text


def build() -> ClaudeApiRunner:
    """後端啟動時建立；沒設定 ANTHROPIC_API_KEY 就拒絕啟動（只檢查有沒有值）。"""
    if not os.environ.get(KEY_ENV):
        raise ConfigError('要接上 Claude（API）必須在啟動後端的環境裡設定 %s' % KEY_ENV)
    return ClaudeApiRunner(anthropic.AsyncAnthropic())
