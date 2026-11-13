"""FR-2 私聊回合的 HTTP 介面：POST 送出（NFR-1 請求 ID）、中斷、GET 查狀態、SSE 推送事件。

回合在伺服器端執行，不受瀏覽器連線影響。SSE 每次都從資料庫讀事件：沒帶 Last-Event-ID 時從頭重送
（網頁重新整理），有帶時只補送之後的事件（網路中斷後自動重連）。
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.turn_contract import TIMEOUT_DEFAULT, request_id as checked_uuid
from app.storage import db, requests, turns
from app.web.runner import StopUnconfirmed


KIND = 'private_turn'
MAX_MESSAGE_CHARS = 32_000  # 預設值，可調（NFR-3 限制大小）

logger = logging.getLogger(__name__)
router = APIRouter()


class TurnRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    request_id: str
    conversation_id: str
    member: str = Field(min_length=1, max_length=160)
    text: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)

    @field_validator('request_id', 'conversation_id')
    @classmethod
    def _uuid(cls, value: str) -> str:
        return checked_uuid(value)


def snapshot(row) -> dict:
    return {
        'id': row['id'],
        'conversation_id': row['conversation_id'],
        'member': row['member'],
        'message': row['message'],
        'state': row['state'],
        'error_kind': row['error_kind'],
        'reply': row['reply'],
        'started': row['started'],
        'finished': row['finished'],
    }


class TurnService:
    """一個 app 一份。runner 照 app/web/runner.py 的介面；None 表示還沒接上轉接器。

    timeout 是單回合逾時（秒）。成員設定（FR-1）做好之前，所有回合都用 TIMEOUT_DEFAULT（15 分鐘）。
    """

    def __init__(self, db_path, runner, *, timeout: float = TIMEOUT_DEFAULT, clock=time.time):
        self.db_path, self.runner, self.timeout, self.clock = db_path, runner, timeout, clock
        self._running: dict[str, asyncio.Task] = {}
        self._interrupts: set[str] = set()
        self._versions: dict[str, int] = {}
        self._waiters: dict[str, asyncio.Event] = {}

    def _connect(self):
        return db.connect(self.db_path)

    def recover(self) -> list[str]:
        connection = self._connect()
        try:
            return turns.mark_running_unknown(connection, self.clock())
        finally:
            connection.close()

    def get(self, turn_id: str):
        connection = self._connect()
        try:
            return turns.get(connection, turn_id)
        finally:
            connection.close()

    def events_after(self, turn_id: str, after: int) -> list[tuple[int, str, dict]]:
        connection = self._connect()
        try:
            return turns.events_after(connection, turn_id, after)
        finally:
            connection.close()

    def version(self, turn_id: str) -> int:
        return self._versions.get(turn_id, 0)

    async def wait_changed(self, turn_id: str, seen: int) -> None:
        while self.version(turn_id) == seen:
            await self._waiters.setdefault(turn_id, asyncio.Event()).wait()

    def _bump(self, turn_id: str) -> None:
        # 同步通知，中間沒有 await：寫完狀態到通知 SSE 之間不會被取消打斷。
        self._versions[turn_id] = self.version(turn_id) + 1
        waiter = self._waiters.pop(turn_id, None)
        if waiter is not None:
            waiter.set()

    def start(self, body: TurnRequest) -> tuple[int, dict]:
        if self.runner is None:
            return 503, {'detail': '尚未接上任何轉接器'}
        payload = {'conversation_id': body.conversation_id, 'member': body.member, 'text': body.text}
        connection = self._connect()
        try:
            claim = requests.claim(
                connection, body.request_id, KIND, payload, clock=self.clock,
                on_claim=lambda c, now: turns.insert_running(c, body.request_id, body.conversation_id,
                                                             body.member, body.text, now))
            row = turns.get(connection, body.request_id)
        except turns.ConversationBusy:
            return 409, {'detail': '這段對話還有進行中的回合'}
        finally:
            connection.close()
        if claim.outcome == requests.REJECTED:
            return 409, {'detail': '這個請求 ID 已用於不同內容'}
        if row is None:
            if claim.state == 'deleted':
                return 410, {'detail': '這個請求所屬的對話已被刪除'}
            return 409, {'detail': '這個請求 ID 已用於其他用途'}
        if claim.outcome == requests.CLAIMED:
            task = asyncio.create_task(self._run(body.request_id, body.member, body.text))
            self._running[body.request_id] = task
            task.add_done_callback(lambda done: self._on_done(body.request_id, done))
            return 202, {'turn': snapshot(row)}
        return 200, {'turn': snapshot(row)}

    def _on_done(self, turn_id: str, task: asyncio.Task) -> None:
        self._running.pop(turn_id, None)
        if task.cancelled() and turn_id in self._interrupts:
            # 中斷在工作開始執行前就送到：執行者沒有被呼叫、沒有程序被啟動，可以直接標為已中斷。
            self._interrupts.discard(turn_id)
            connection = self._connect()
            try:
                turns.finish(connection, turn_id, turns.INTERRUPTED, self.clock())
            finally:
                connection.close()
            self._bump(turn_id)

    def interrupt(self, turn_id: str) -> tuple[int, dict]:
        """擁有者按「中斷」：要求執行者停止。結果（已中斷或未知）由 SSE 的 done 事件告知。"""
        row = self.get(turn_id)
        if row is None:
            return 404, {'detail': '找不到這個回合'}
        task = self._running.get(turn_id)
        if row['state'] != turns.RUNNING or task is None or task.done():
            return 409, {'detail': '回合已經結束', 'turn': snapshot(row)}
        if turn_id not in self._interrupts:
            self._interrupts.add(turn_id)
            task.cancel()
        return 202, {'turn': snapshot(row)}

    def conversation(self, conversation_id: str) -> list:
        connection = self._connect()
        try:
            return turns.conversation(connection, conversation_id)
        finally:
            connection.close()

    def delete_conversation(self, conversation_id: str) -> int:
        connection = self._connect()
        try:
            deleted = turns.delete_conversation(connection, conversation_id, self.clock())
            if deleted and not db.truncate_wal(connection):
                # 有其他連線正在讀；WAL 裡的舊內容會在之後的檢查點清掉。
                logger.warning('刪除對話後 WAL 未能立即清空')
            return deleted
        finally:
            connection.close()

    async def _run(self, turn_id: str, member: str, text: str) -> None:
        async def emit(data: dict) -> None:
            connection = self._connect()
            try:
                turns.append_progress(connection, turn_id, data, self.clock())
            finally:
                connection.close()
            self._bump(turn_id)

        deadline = asyncio.timeout(self.timeout)
        try:
            async with deadline:
                reply = await self.runner(member, text, emit)
            if not isinstance(reply, str):
                raise TypeError('回覆必須是文字')
            outcome = {'state': turns.COMPLETED, 'reply': reply}
        except StopUnconfirmed:
            # 中斷、逾時或關閉時，執行者無法確認程序已停止（FR-2：未知）。
            outcome = {'state': turns.UNKNOWN}
        except asyncio.CancelledError:
            if turn_id not in self._interrupts:
                raise  # 伺服器關閉：回合留在進行中，下次啟動時標為未知
            outcome = {'state': turns.INTERRUPTED}  # 執行者已確認程序停止
        except TimeoutError:
            if deadline.expired():
                outcome = {'state': turns.FAILED, 'error_kind': turns.TIMEOUT}
            else:  # 執行者自己丟出的 TimeoutError，不是單回合逾時
                logger.warning('回合 %s 失敗：TimeoutError', turn_id)
                outcome = {'state': turns.FAILED, 'error_kind': turns.INTERNAL_ERROR}
        except Exception as exc:
            # 只記錄分類與例外類型，不記錄訊息內容（NFR-6）。
            logger.warning('回合 %s 失敗：%s', turn_id, type(exc).__name__)
            outcome = {'state': turns.FAILED, 'error_kind': turns.INTERNAL_ERROR}
        if turn_id in self._interrupts:
            self._interrupts.discard(turn_id)
            task = asyncio.current_task()
            if task is not None and task.cancelling():
                task.uncancel()  # 中斷要求已處理完，不再往外傳取消
        # 以下沒有 await：寫入結束狀態與通知 SSE 不會被取消打斷。
        connection = self._connect()
        try:
            turns.finish(connection, turn_id, now=self.clock(), **outcome)
        finally:
            connection.close()
        self._bump(turn_id)

    async def close(self) -> None:
        tasks = list(self._running.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


def _service(request: Request) -> TurnService:
    return request.app.state.turns


def _existing_turn(turn_id: str, service: Annotated[TurnService, Depends(_service)]):
    row = service.get(turn_id)
    if row is None:
        raise HTTPException(status_code=404, detail='找不到這個回合')
    return row


def _conversation_id(conversation_id: str) -> str:
    try:
        return checked_uuid(conversation_id)
    except ValueError:
        raise HTTPException(status_code=422, detail='對話識別無效') from None


@router.get('/api/conversations/{conversation_id}')
def get_conversation(conversation_id: Annotated[str, Depends(_conversation_id)],
                     service: Annotated[TurnService, Depends(_service)]):
    rows = service.conversation(conversation_id)
    if not rows:
        raise HTTPException(status_code=404, detail='找不到這段對話')
    return {'conversation_id': conversation_id, 'turns': [snapshot(row) for row in rows]}


@router.delete('/api/conversations/{conversation_id}', status_code=204)
def delete_conversation(conversation_id: Annotated[str, Depends(_conversation_id)],
                        service: Annotated[TurnService, Depends(_service)]):
    try:
        deleted = service.delete_conversation(conversation_id)
    except turns.ConversationBusy:
        raise HTTPException(status_code=409, detail='這段對話還有進行中的回合，不能刪除') from None
    if not deleted:
        raise HTTPException(status_code=404, detail='找不到這段對話')


@router.post('/api/turns')
async def start_turn(body: TurnRequest, service: Annotated[TurnService, Depends(_service)]):
    status, content = service.start(body)
    return JSONResponse(content, status_code=status)


@router.post('/api/turns/{turn_id}/interrupt')
# async：要在事件迴圈裡取消工作，不能丟到執行緒池。
async def interrupt_turn(turn_id: str, service: Annotated[TurnService, Depends(_service)]):
    status, content = service.interrupt(turn_id)
    return JSONResponse(content, status_code=status)


@router.get('/api/turns/{turn_id}')
def get_turn(row: Annotated[object, Depends(_existing_turn)]):
    return {'turn': snapshot(row)}


@router.get('/api/turns/{turn_id}/events', response_class=EventSourceResponse)
async def turn_events(turn_id: str, row: Annotated[object, Depends(_existing_turn)],
                      service: Annotated[TurnService, Depends(_service)],
                      last_event_id: Annotated[str | None, Header()] = None):
    after = int(last_event_id) if last_event_id and last_event_id.isascii() and last_event_id.isdigit() else 0
    while True:
        seen = service.version(turn_id)
        pending = service.events_after(turn_id, after)
        for seq, kind, data in pending:
            if kind == turns.DONE:
                data = {**data, 'reply': service.get(turn_id)['reply']}
            yield ServerSentEvent(id=str(seq), event=kind, data=data)
            after = seq
            if kind == turns.DONE:
                return
        if not pending:
            await service.wait_changed(turn_id, seen)
