"""FR-2 私聊回合的狀態與事件。

資料庫是唯一的狀態來源：網頁重新整理時由這裡重送完整事件，不依賴瀏覽器的 Last-Event-ID。
不存使用者訊息全文（NFR-6）；錯誤只存固定分類，不存原始錯誤訊息。
"""
from __future__ import annotations

import json
import sqlite3


RUNNING = 'running'
COMPLETED = 'completed'
FAILED = 'failed'
INTERRUPTED = 'interrupted'
UNKNOWN = 'unknown'
FINAL_STATES = frozenset({COMPLETED, FAILED, INTERRUPTED, UNKNOWN})

# 失敗原因的固定分類；接上真的轉接器時再加（例如額度不足、認證失敗、逾時）。
INTERNAL_ERROR = 'internal_error'
ERROR_KINDS = frozenset({INTERNAL_ERROR})

PROGRESS = 'progress'
DONE = 'done'


class ConversationBusy(RuntimeError):
    pass


def insert_running(connection: sqlite3.Connection, turn_id: str, conversation_id: str, member: str,
                   now: float) -> None:
    """必須在呼叫者的交易裡執行（requests.claim 的 on_claim）。"""
    busy = connection.execute('SELECT 1 FROM turns WHERE conversation_id = ? AND state = ?',
                              (conversation_id, RUNNING)).fetchone()
    if busy:
        raise ConversationBusy('這段對話還有進行中的回合')
    try:
        connection.execute('INSERT INTO turns (id, conversation_id, member, state, started) VALUES (?, ?, ?, ?, ?)',
                           (turn_id, conversation_id, member, RUNNING, now))
    except sqlite3.IntegrityError as exc:
        raise ConversationBusy('這段對話還有進行中的回合') from exc


def get(connection: sqlite3.Connection, turn_id: str) -> sqlite3.Row | None:
    return connection.execute('SELECT * FROM turns WHERE id = ?', (turn_id,)).fetchone()


def events_after(connection: sqlite3.Connection, turn_id: str, after: int) -> list[tuple[int, str, dict]]:
    rows = connection.execute('SELECT seq, kind, data FROM turn_events WHERE turn_id = ? AND seq > ? ORDER BY seq',
                              (turn_id, after)).fetchall()
    return [(row['seq'], row['kind'], json.loads(row['data'])) for row in rows]


def _append(connection: sqlite3.Connection, turn_id: str, kind: str, data: dict, now: float) -> int:
    seq = connection.execute('SELECT COALESCE(MAX(seq), 0) + 1 FROM turn_events WHERE turn_id = ?',
                             (turn_id,)).fetchone()[0]
    connection.execute('INSERT INTO turn_events (turn_id, seq, kind, data, created) VALUES (?, ?, ?, ?, ?)',
                       (turn_id, seq, kind, json.dumps(data, ensure_ascii=False, allow_nan=False), now))
    return seq


def append_progress(connection: sqlite3.Connection, turn_id: str, data: dict, now: float) -> int | None:
    """回合已結束時不再寫入，回傳 None。"""
    connection.execute('BEGIN IMMEDIATE')
    try:
        row = get(connection, turn_id)
        seq = _append(connection, turn_id, PROGRESS, data, now) if row and row['state'] == RUNNING else None
        connection.execute('COMMIT')
    except BaseException:
        connection.execute('ROLLBACK')
        raise
    return seq


def _finish_in_transaction(connection, turn_id, state, now, reply, error_kind) -> bool:
    updated = connection.execute('UPDATE turns SET state = ?, reply = ?, error_kind = ?, finished = ?'
                                 ' WHERE id = ? AND state = ?',
                                 (state, reply, error_kind, now, turn_id, RUNNING)).rowcount
    if updated:
        _append(connection, turn_id, DONE, {'state': state, 'error_kind': error_kind}, now)
    return bool(updated)


def finish(connection: sqlite3.Connection, turn_id: str, state: str, now: float, *,
           reply: str | None = None, error_kind: str | None = None) -> bool:
    """把進行中的回合標為結束並寫入 done 事件；回合不是進行中時不動，回傳 False。"""
    if state not in FINAL_STATES:
        raise ValueError('結束狀態無效')
    if (state == COMPLETED) != (reply is not None):
        raise ValueError('只有完成的回合有回覆')
    if (state == FAILED) != (error_kind is not None) or (error_kind is not None and error_kind not in ERROR_KINDS):
        raise ValueError('失敗原因無效')
    connection.execute('BEGIN IMMEDIATE')
    try:
        done = _finish_in_transaction(connection, turn_id, state, now, reply, error_kind)
        connection.execute('COMMIT')
    except BaseException:
        connection.execute('ROLLBACK')
        raise
    return done


def mark_running_unknown(connection: sqlite3.Connection, now: float) -> list[str]:
    """伺服器啟動時呼叫：上次執行留下、已經沒有程序在跑的回合，查不回結果，一律標為未知（FR-2）。"""
    connection.execute('BEGIN IMMEDIATE')
    try:
        ids = [row['id'] for row in connection.execute('SELECT id FROM turns WHERE state = ?', (RUNNING,))]
        for turn_id in ids:
            _finish_in_transaction(connection, turn_id, UNKNOWN, now, None, None)
        connection.execute('COMMIT')
    except BaseException:
        connection.execute('ROLLBACK')
        raise
    return ids
