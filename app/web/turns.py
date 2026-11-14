"""FR-2 私聊回合的 HTTP 介面：POST 送出（NFR-1 請求 ID）、中斷、GET 查狀態、SSE 推送事件。

回合在伺服器端執行，不受瀏覽器連線影響。SSE 每次都從資料庫讀事件：沒帶 Last-Event-ID 時從頭重送
（網頁重新整理），有帶時只補送之後的事件（網路中斷後自動重連）。
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel, ConfigDict, Field, field_validator

from collections.abc import Mapping

from app.services.turn_contract import request_id as checked_uuid
from app.storage import db, members, requests, turns
from app.web.runner import Failed, Hooks, Interrupted, TurnInput, Unknown


KIND = 'private_turn'
MAX_MESSAGE_CHARS = 32_000  # 預設值，可調（NFR-3 限制大小）
MAX_REPLY_BYTES = 100_000  # FR-2 回覆長度上限（UTF-8 位元組），預設值

logger = logging.getLogger(__name__)
router = APIRouter()


class TurnRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    request_id: str
    conversation_id: str
    member: str  # 成員 ID（FR-1）
    text: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)

    @field_validator('request_id', 'conversation_id', 'member')
    @classmethod
    def _uuid(cls, value: str) -> str:
        return checked_uuid(value)


def snapshot(row) -> dict:
    return {
        'id': row['id'],
        'conversation_id': row['conversation_id'],
        'member': row['member'],
        'member_name': row['member_name'],  # 送出時的成員名稱；成員刪除後照樣顯示
        'adapter': row['adapter'],
        'message': row['message'],
        'state': row['state'],
        'error_kind': row['error_kind'],
        'reply': row['reply'],
        'started': row['started'],
        'finished': row['finished'],
    }


class MemberUnavailable(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status, self.detail = status, detail


class TurnService:
    """一個 app 一份。runner 照 app/web/runner.py 的介面：單一執行者（所有轉接器共用，例如假轉接器）、
    {轉接器代號: 執行者}，或 None（還沒接上任何轉接器）。

    單回合逾時取自成員設定（FR-1），交給轉接器或它的橋接執行。timeout 不是 None 時改用它（只供測試縮短）。
    """

    def __init__(self, db_path, runner, *, timeout: float | None = None, clock=time.time):
        self.db_path, self.runner, self.timeout, self.clock = db_path, runner, timeout, clock
        self._running: dict[str, asyncio.Task] = {}
        self._versions: dict[str, int] = {}
        self._waiters: dict[str, asyncio.Event] = {}

    def _connect(self):
        return db.connect(self.db_path)

    def runner_for(self, adapter: str | None):
        if isinstance(self.runner, Mapping):
            return self.runner.get(adapter)
        return self.runner

    def recover(self) -> list[str]:
        """伺服器啟動時呼叫（要在事件迴圈裡）：上次留下的進行中回合，有轉接器身分的交給 resume 接回，
        其餘標為未知。回傳標為未知的回合 ID。"""
        connection = self._connect()
        resumable = []
        try:
            now = self.clock()
            unknown = turns.mark_running_unknown(connection, now, keep_recorded=self.runner is not None)
            for turn_id, text, adapter in turns.recorded_running(connection) if self.runner is not None else ():
                try:
                    record = json.loads(text)
                except ValueError:
                    record = None
                runner = self.runner_for(adapter)
                if isinstance(record, dict) and runner is not None:
                    resumable.append((turn_id, record, runner))
                elif turns.finish(connection, turn_id, turns.UNKNOWN, now):
                    unknown.append(turn_id)
        finally:
            connection.close()
        for turn_id, record, runner in resumable:
            self._spawn(turn_id, lambda hooks, t=turn_id, r=record, x=runner: self._resume(x, t, r, hooks))
        return unknown

    async def _resume(self, runner, turn_id: str, record: dict, hooks: Hooks) -> None:
        try:
            await runner.resume(turn_id, record, hooks)
        except NotImplementedError:
            raise Unknown('resume_unsupported') from None

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
        picked = {}

        def claim_turn(connection, now):
            # 在同一個交易裡查成員：檢查到寫入之間成員不會被改掉或刪掉。
            member = members.get(connection, body.member)
            if member is None:
                raise MemberUnavailable(422, '找不到這位成員')
            if not member['enabled']:
                raise MemberUnavailable(409, '這位成員已停用')
            if self.runner_for(member['adapter']) is None:
                raise MemberUnavailable(503, '這位成員的轉接器還沒接上')
            turns.insert_running(connection, body.request_id, body.conversation_id, body.member, body.text, now,
                                 member_name=member['name'], adapter=member['adapter'])
            picked['member'] = member

        connection = self._connect()
        try:
            claim = requests.claim(connection, body.request_id, KIND, payload, clock=self.clock,
                                   on_claim=claim_turn)
            row = turns.get(connection, body.request_id)
        except turns.ConversationBusy:
            return 409, {'detail': '這段對話還有進行中的回合'}
        except turns.ConversationMemberMismatch:
            return 409, {'detail': '這段對話屬於另一位成員，請開新對話'}
        except MemberUnavailable as exc:
            return exc.status, {'detail': exc.detail}
        finally:
            connection.close()
        if claim.outcome == requests.REJECTED:
            return 409, {'detail': '這個請求 ID 已用於不同內容'}
        if row is None:
            if claim.state == 'deleted':
                return 410, {'detail': '這個請求所屬的對話已被刪除'}
            return 409, {'detail': '這個請求 ID 已用於其他用途'}
        if claim.outcome == requests.CLAIMED:
            member = picked['member']
            turn = TurnInput(body.request_id, body.conversation_id, body.member, body.text,
                             self.timeout if self.timeout is not None else member['timeout'],
                             adapter=member['adapter'], model=member['model'], effort=member['effort'],
                             auth_mode=member['auth_mode'])
            runner = self.runner_for(member['adapter'])
            self._spawn(body.request_id, lambda hooks: runner.run(turn, hooks))
            return 202, {'turn': snapshot(row)}
        return 200, {'turn': snapshot(row)}

    def _spawn(self, turn_id: str, call) -> None:
        task = asyncio.create_task(self._drive(turn_id, call))
        self._running[turn_id] = task
        task.add_done_callback(lambda _: self._running.pop(turn_id, None))

    async def interrupt(self, turn_id: str) -> tuple[int, dict]:
        """擁有者按「中斷」：把要求交給轉接器，送達後寫「中斷中」事件。
        結果（已中斷或未知）由 SSE 的 done 事件告知。"""
        row = self.get(turn_id)
        if row is None:
            return 404, {'detail': '找不到這個回合'}
        task = self._running.get(turn_id)
        if row['state'] != turns.RUNNING or task is None or task.done():
            return 409, {'detail': '回合已經結束', 'turn': snapshot(row)}
        try:
            runner = self.runner_for(row['adapter'])
            if runner is None:
                raise LookupError('沒有這個轉接器的執行者')
            await runner.stop(turn_id)
        except Exception as exc:
            logger.warning('回合 %s 的中斷要求沒有送達：%s', turn_id, type(exc).__name__)
            return 502, {'detail': '中斷要求沒有送達轉接器，回合可能仍在執行', 'turn': snapshot(self.get(turn_id) or row)}
        connection = self._connect()
        try:
            stopping = turns.mark_stopping(connection, turn_id, self.clock())
        finally:
            connection.close()
        if stopping is not None:
            self._bump(turn_id)
        return 202, {'turn': snapshot(self.get(turn_id) or row)}

    def conversation(self, conversation_id: str) -> list:
        connection = self._connect()
        try:
            return turns.conversation(connection, conversation_id)
        finally:
            connection.close()

    def conversations(self) -> list[dict]:
        connection = self._connect()
        try:
            return turns.conversations(connection)
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

    def _finish(self, turn_id: str, state: str, **outcome) -> bool:
        # 沒有 await：寫入結束狀態與通知 SSE 不會被取消打斷。
        connection = self._connect()
        try:
            done = turns.finish(connection, turn_id, state, self.clock(), **outcome)
        finally:
            connection.close()
        self._bump(turn_id)
        return done

    async def _drive(self, turn_id: str, call) -> None:
        """執行 call(hooks)（runner.run 或 resume），把結果對應到回合狀態（見 app/web/runner.py）。"""
        settled = False  # save 已寫入結果：完成，或因回覆過長而失敗

        def began(record: dict) -> None:  # 可能在其他執行緒
            connection = self._connect()
            try:
                if not turns.save_record(connection, turn_id, record):
                    raise RuntimeError('回合已不在進行中')
            finally:
                connection.close()

        def progress(item: dict) -> None:
            connection = self._connect()
            try:
                turns.append_progress(connection, turn_id, item, self.clock())
            finally:
                connection.close()
            self._bump(turn_id)

        def save(reply: str) -> None:
            nonlocal settled
            if not isinstance(reply, str):
                raise TypeError('回覆必須是文字')
            size = len(reply.encode('utf-8'))
            if size > MAX_REPLY_BYTES:
                # FR-2：明確告知、不截斷，回覆一個字都不存。照常返回，轉接器可以讓遠端丟掉回覆。
                logger.warning('回合 %s 失敗：回覆過長（%d 位元組）', turn_id, size)
                result = {'state': turns.FAILED, 'error_kind': turns.REPLY_TOO_LONG}
            else:
                result = {'state': turns.COMPLETED, 'reply': reply}
            if not self._finish(turn_id, **result):
                # 沒寫進去就不能讓轉接器通知遠端丟掉回覆。
                raise RuntimeError('回合已不在進行中，結果沒有存下')
            settled = True

        outcome = None
        try:
            await call(Hooks(began, progress, save))
            if not settled:
                logger.warning('回合 %s 失敗：轉接器沒有交出回覆', turn_id)
                outcome = {'state': turns.FAILED, 'error_kind': turns.INTERNAL_ERROR}
        except Interrupted:
            outcome = {'state': turns.INTERRUPTED}  # 轉接器已確認程序停止
        except Unknown:
            outcome = {'state': turns.UNKNOWN}  # FR-2：無法確認時標為未知
        except Failed as exc:
            kind = exc.kind if exc.kind in turns.ERROR_KINDS else turns.INTERNAL_ERROR
            outcome = {'state': turns.FAILED, 'error_kind': kind}
        except asyncio.CancelledError:
            raise  # 伺服器關閉：回合留在進行中，下次啟動時接回或標為未知
        except Exception as exc:
            # 只記錄分類與例外類型，不記錄訊息內容（NFR-6）。
            logger.warning('回合 %s 失敗：%s', turn_id, type(exc).__name__)
            outcome = {'state': turns.FAILED, 'error_kind': turns.INTERNAL_ERROR}
        if outcome is not None and not settled:
            self._finish(turn_id, **outcome)

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


@router.get('/api/conversations')
def list_conversations(service: Annotated[TurnService, Depends(_service)]):
    return {'conversations': service.conversations()}


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
async def interrupt_turn(turn_id: str, service: Annotated[TurnService, Depends(_service)]):
    status, content = await service.interrupt(turn_id)
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
