"""開發與測試用的假轉接器：不呼叫任何 AI，依序送出幾個進度後回覆一段固定文字。

只有設定 YIQUNREN_FAKE_TURNS=1，或測試直接注入時才會使用。回覆不引用使用者訊息內容。
停止行為照 app/web/runner.py 的介面：被取消時預設視為已確認停止；stop_confirmed=False 時模擬無法確認。
"""
from __future__ import annotations

import asyncio
import time

from app.web.runner import StopUnconfirmed


class FakeRunner:
    def __init__(self, steps: int = 3, tick: float = 1.0, *, stop_confirmed: bool = True):
        self.steps, self.tick, self.stop_confirmed = steps, tick, stop_confirmed

    async def __call__(self, member: str, text: str, emit) -> str:
        started = time.monotonic()
        try:
            for step in range(1, self.steps + 1):
                await asyncio.sleep(self.tick)
                await emit({'step': step, 'of': self.steps, 'elapsed': round(time.monotonic() - started, 1)})
        except asyncio.CancelledError:
            if not self.stop_confirmed:
                raise StopUnconfirmed() from None
            raise
        return '（模擬回覆）已收到 %d 個字。' % len(text)
