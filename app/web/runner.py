"""私聊回合執行者（轉接器）要遵守的介面。

執行者繼承 Runner，實作：

    async def run(self, turn: TurnInput, hooks: Hooks) -> None
    async def resume(self, turn_id: str, record: dict, hooks: Hooks) -> None   # 可選
    async def stop(self, turn_id: str) -> None

結果怎麼回報（FR-2）：
- 完成：呼叫 hooks.save(回覆文字)，再正常返回。save 返回時回合已標為完成並寫進資料庫；
  遠端若要等 App 存好才丟掉回覆（例如 worker_turn 的 ack），必須在 save 返回之後才通知。
- 擁有者中斷，且確認程序已經停止：丟 Interrupted。
- 結果無法確認（停止未確認、橋接重啟、查回逾時、連不上橋接）：丟 Unknown(原因)。
- 失敗：丟 Failed(分類)。分類不在固定清單時記為 internal_error；其他例外也一律是 internal_error。
  只存分類，不存原始錯誤訊息。
- 返回卻沒有呼叫 save：記為 internal_error。

停止：擁有者按「中斷」時，系統呼叫 stop(turn_id)，不取消 asyncio 工作。stop 只負責把要求送出，
送出就返回（送不出去就丟例外）；結果由 run／resume 丟出 Interrupted 或 Unknown 告知。
stop 可能在 run／resume 開始之前就送到，執行者必須記住，開始時就照辦。

逾時：由轉接器或它的橋接負責，秒數是 TurnInput.timeout。逾時且確認程序已經停止丟 Failed('timeout')，
無法確認丟 Unknown。

取消：asyncio 取消只代表伺服器要關閉。執行者不要因此停止遠端的回合，讓 CancelledError 照常往外傳；
回合在資料庫裡維持「執行中」，下次啟動時，有 began 紀錄的用 resume 接回，沒有的標為未知。

hooks：
- began(record)：遠端接受回合後呼叫。record 是可轉成 JSON 的 dict，存進資料庫給重啟後的 resume 用，
  只放接回所需的身分，不放訊息、回覆或憑證。可以在其他執行緒呼叫（只寫資料庫）；
  失敗時會丟例外，執行者應要求遠端停止這一回合並丟 Unknown。
- progress(item)：送出進度，只放可以公開的資訊。必須在事件迴圈的執行緒呼叫。
- save(reply)：見上。必須在事件迴圈的執行緒呼叫。

resume：用 began 存下的 record 接回上次執行中的回合，結果照 run 的方式回報。
不支援接回的執行者不必實作（預設丟 NotImplementedError，回合標為未知）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class TurnInput:
    turn_id: str
    conversation_id: str
    member: str
    message: str
    timeout: float  # 秒


@dataclass(frozen=True)
class Hooks:
    began: Callable[[dict], None]
    progress: Callable[[dict], None]
    save: Callable[[str], None]


class Interrupted(Exception):
    """擁有者中斷，且已確認程序停止。"""


class Unknown(Exception):
    """結果無法確認。reason 是固定的原因代號，只用於診斷，不顯示原始錯誤訊息。"""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class Failed(Exception):
    """回合失敗；kind 是固定分類（app.storage.turns.ERROR_KINDS）。"""

    def __init__(self, kind: str):
        super().__init__(kind)
        self.kind = kind


class Runner:
    async def run(self, turn: TurnInput, hooks: Hooks) -> None:
        raise NotImplementedError

    async def resume(self, turn_id: str, record: dict, hooks: Hooks) -> None:
        raise NotImplementedError

    async def stop(self, turn_id: str) -> None:
        raise NotImplementedError
