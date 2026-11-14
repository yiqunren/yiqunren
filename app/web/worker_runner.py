"""接到各家 CLI 橋接的私聊執行者：包住 app/services/worker_turn.py 的非同步回合協定。

- run：turn_begin → 橋接接受後，經 began 把回合身分（worker_turn.Handle.record()）存進資料庫 →
  每隔一段時間 turn_status 查回 → 完成時先 save，save 成功後才 turn_ack 讓橋接丟掉回覆全文。
- stop：turn_stop。橋接確認程序群組結束才回報 stopped（→ Interrupted），確認不了回報 unknown（→ Unknown）。
- resume：伺服器重啟後用存下的身分查回。橋接也重啟過（epoch 不同）時是 Unknown('bridge_restarted')。
- 逾時由橋接執行（turn_begin 帶 timeout）；橋接逾時目前回報為一般失敗（internal_error），
  橋接協定加上錯誤分類後才能分出 timeout。
- 伺服器關閉（asyncio 取消）時不送 turn_stop，回合留在橋接繼續跑，重啟後用 resume 接回。

已知限制：resume 從頭查回進度，重啟前已記錄的進度項可能再記一次（只影響進度顯示）。
"""
from __future__ import annotations

import asyncio
from contextlib import contextmanager
import logging
import re
from typing import Callable

from app.services import adapters, worker_turn
from app.storage.turns import INTERNAL_ERROR
from app.web.runner import Failed, Hooks, Interrupted, Runner, TurnInput, Unknown


logger = logging.getLogger(__name__)

# 送出暫存的中斷要求時，最多等多久（秒）；比 worker_turn 的控制請求上限多留一點。
PENDING_STOP_WAIT = worker_turn.CONTROL_TIMEOUT + 5


class WorkerTurnRunner(Runner):
    """provider：轉接器代號；fields(turn)：產生該家 turn_begin 的欄位。認證模式取自回合（成員設定，FR-1）。"""

    def __init__(self, provider: str, *, fields: Callable[[TurnInput], dict]):
        adapters.get(provider)  # 未登記的代號直接拒絕
        self.provider, self.fields = provider, fields
        self._tracks: dict[str, worker_turn.Track] = {}
        self._handles: dict[str, worker_turn.Handle] = {}
        self._pending: set[str] = set()  # 還沒拿到橋接身分就送到的中斷要求

    async def run(self, turn: TurnInput, hooks: Hooks) -> None:
        if turn.turn_id in self._pending:
            self._pending.discard(turn.turn_id)
            raise Interrupted()  # 還沒送出 turn_begin，沒有任何程序被啟動
        loop = asyncio.get_running_loop()
        record_failed = False

        def on_begin(handle: worker_turn.Handle) -> None:  # worker_turn 在執行緒呼叫
            nonlocal record_failed
            try:
                hooks.began(handle.record())
            except Exception:
                record_failed = True  # worker_turn 會要求橋接停止這一回合
                raise
            if turn.turn_id in self._pending:
                future = asyncio.run_coroutine_threadsafe(worker_turn.stop_handle(handle), loop)
                try:
                    future.result(PENDING_STOP_WAIT)
                except Exception:
                    logger.warning('回合 %s 的中斷要求未能送達橋接', turn.turn_id)

        try:
            async with worker_turn.tracked(None, timeout=int(turn.timeout), on_begin=on_begin) as track:
                self._tracks[turn.turn_id] = track
                with _mapped(lambda: record_failed):
                    result = await worker_turn.run(self.provider, self.fields(turn), auth_mode=turn.auth_mode,
                                                   on_progress=hooks.progress)
                # 區塊正常結束（save 成功）後 tracked 才送 turn_ack；save 失敗就不 ack，橋接保留回覆。
                hooks.save(_content(result), session=_session(result))
        finally:
            self._tracks.pop(turn.turn_id, None)
            self._pending.discard(turn.turn_id)

    async def resume(self, turn_id: str, record: dict, hooks: Hooks) -> None:
        try:
            handle = worker_turn.Handle.from_record(record)
        except (KeyError, TypeError, ValueError):
            raise Unknown('record_invalid') from None
        self._handles[turn_id] = handle
        try:
            with _mapped(lambda: False):
                if turn_id in self._pending:
                    try:
                        await worker_turn.stop_handle(handle)
                    except Exception:
                        logger.warning('回合 %s 的中斷要求未能送達橋接', turn_id)
                result = await worker_turn.observe(handle, on_progress=hooks.progress)
            hooks.save(_content(result), session=_session(result))
        finally:
            self._handles.pop(turn_id, None)
            self._pending.discard(turn_id)
        await worker_turn.ack(handle)  # 存好之後才讓橋接丟掉回覆

    async def stop(self, turn_id: str) -> None:
        handle = self._handles.get(turn_id)
        if handle is None:
            track = self._tracks.get(turn_id)
            handle = track.handle if track is not None else None
        if handle is None:
            # turn_begin 還沒送出或還在路上：先記下，拿到身分後（on_begin）再送 turn_stop。
            self._pending.add(turn_id)
            return
        await worker_turn.stop_handle(handle)


def _content(result) -> str:
    content = result.get('content') if isinstance(result, dict) else None
    if not isinstance(content, str):
        raise Failed(INTERNAL_ERROR)
    return content


SESSION = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}')


def _session(result) -> str | None:
    """橋接回報的該家對話身分（NFR-7 續接）；沒有或格式不對就當沒有，不影響回覆。"""
    session = result.get('session') if isinstance(result, dict) else None
    return session if isinstance(session, str) and SESSION.fullmatch(session) else None


@contextmanager
def _mapped(record_failed: Callable[[], bool]):
    """只包住和橋接往來的呼叫：worker_turn 的例外 → 執行者介面的結果；
    其他例外照原樣往外傳（記為 internal_error）。"""
    try:
        yield
    except worker_turn.TurnInterrupted:
        raise Interrupted() from None
    except worker_turn.TurnUnknown as exc:
        raise Unknown(exc.reason) from None
    except (TimeoutError, OSError):
        # turn_begin 送出後沒收到回覆：橋接可能已經開始執行，結果無法確認。
        raise Unknown('transport') from None
    except RuntimeError:
        if record_failed():
            raise Unknown('record_failed') from None
        raise
