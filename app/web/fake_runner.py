"""開發與測試用的假轉接器：不呼叫任何 AI，依序送出幾個進度後回覆一段固定文字。

只有設定 YIQUNREN_FAKE_TURNS=1，或測試直接注入時才會使用。回覆不引用使用者訊息內容。
"""
from __future__ import annotations

import asyncio
import time


class FakeRunner:
    def __init__(self, steps: int = 3, tick: float = 1.0):
        self.steps, self.tick = steps, tick

    async def __call__(self, member: str, text: str, emit) -> str:
        started = time.monotonic()
        for step in range(1, self.steps + 1):
            await asyncio.sleep(self.tick)
            await emit({'step': step, 'of': self.steps, 'elapsed': round(time.monotonic() - started, 1)})
        return '（模擬回覆）已收到 %d 個字。' % len(text)
