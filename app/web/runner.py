"""私聊回合執行者（轉接器）要遵守的介面。

執行者是一個 async callable：

    async def runner(member: str, text: str, emit) -> str

- 回傳值是成員的回覆文字。
- 進度用 `await emit({...})` 送出；內容只放可以公開的進度資訊，不放提示詞或憑證。
- 停止：系統要停止回合時（擁有者中斷、單回合逾時、伺服器關閉），會取消執行這個回合的 asyncio 工作，
  執行者在目前的 await 收到 asyncio.CancelledError。執行者必須在有限時間內停止底下的程序：
  - 確認程序已經停止：讓 CancelledError 照常往外傳（可以先清理再重新丟出）。
  - 無法確認程序是否停止：改丟 StopUnconfirmed。
  這對應 FR-2「已中斷：確認成員的程序已經停止後才標示；無法確認時標為未知」。
- 其他例外一律當成失敗，只記固定分類，不顯示原始錯誤訊息。
"""
from __future__ import annotations


class StopUnconfirmed(Exception):
    """執行者被要求停止，但無法確認底下的程序已經停止。"""
