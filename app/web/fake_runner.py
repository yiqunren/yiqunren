"""開發與測試用的假轉接器：不呼叫任何 AI，依序送出幾個進度後回覆一段固定文字。

只有設定 YIQUNREN_FAKE_TURNS=1，或測試直接注入時才會使用。回覆不引用使用者訊息內容。
介面照 app/web/runner.py：中斷與逾時預設視為已確認停止；stop_confirmed=False 時模擬無法確認。
不支援重啟後接回（沒有呼叫 began），所以伺服器重啟時執行中的假回合會標為未知。
"""
from __future__ import annotations

import asyncio

from app.storage.turns import TIMEOUT
from app.web.runner import Failed, Hooks, Interrupted, Runner, TurnInput, Unknown


class FakeRunner(Runner):
    def __init__(self, steps: int = 3, tick: float = 1.0, *, stop_confirmed: bool = True):
        self.steps, self.tick, self.stop_confirmed = steps, tick, stop_confirmed
        self._stops: set[str] = set()
        self._wakeups: dict[str, asyncio.Event] = {}

    async def run(self, turn: TurnInput, hooks: Hooks) -> None:
        loop = asyncio.get_running_loop()
        started = loop.time()
        deadline = started + turn.timeout
        wakeup = self._wakeups[turn.turn_id] = asyncio.Event()
        try:
            for step in range(1, self.steps + 1):
                tick_end = loop.time() + self.tick
                while True:
                    now = loop.time()
                    if turn.turn_id in self._stops:
                        raise Interrupted() if self.stop_confirmed else Unknown('stop_unconfirmed')
                    if now >= deadline:
                        raise Failed(TIMEOUT) if self.stop_confirmed else Unknown('stop_unconfirmed')
                    if now >= tick_end:
                        break
                    try:
                        await asyncio.wait_for(wakeup.wait(), min(tick_end, deadline) - now)
                    except TimeoutError:
                        pass
                hooks.progress({'step': step, 'of': self.steps, 'elapsed': round(loop.time() - started, 1)})
            hooks.save('（模擬回覆）已收到 %d 個字。' % len(turn.message))
        finally:
            self._stops.discard(turn.turn_id)
            self._wakeups.pop(turn.turn_id, None)

    async def stop(self, turn_id: str) -> None:
        self._stops.add(turn_id)
        wakeup = self._wakeups.get(turn_id)
        if wakeup is not None:
            wakeup.set()
