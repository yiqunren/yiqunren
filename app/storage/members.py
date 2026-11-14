"""FR-1 成員設定的資料存取。

這裡只負責存取；轉接器、認證模式、推理強度是否合法，由 app/web/members.py 依轉接器登記處檢查。
不存任何憑證（NFR-4）。
"""
from __future__ import annotations

import sqlite3

from app.storage import turns


IDLE = 'idle'
RUNNING = 'running'
NEEDS_REVIEW = 'needs_review'

EDITABLE = frozenset({'name', 'model', 'effort', 'auth_mode', 'timeout', 'enabled'})


class MemberBusy(RuntimeError):
    pass


def insert(connection: sqlite3.Connection, member_id: str, *, adapter: str, name: str, model: str,
           effort: str | None, auth_mode: str, timeout: int, now: float) -> None:
    """必須在呼叫者的交易裡執行（requests.claim 的 on_claim）。"""
    connection.execute('INSERT INTO members (id, adapter, name, model, effort, auth_mode, timeout, enabled,'
                       ' created, updated) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)',
                       (member_id, adapter, name, model, effort, auth_mode, timeout, now, now))


def get(connection: sqlite3.Connection, member_id: str) -> sqlite3.Row | None:
    return connection.execute('SELECT * FROM members WHERE id = ?', (member_id,)).fetchone()


def all_members(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return connection.execute('SELECT * FROM members ORDER BY created, rowid').fetchall()


def update(connection: sqlite3.Connection, member_id: str, changes: dict, now: float) -> bool:
    """只改 EDITABLE 裡的欄位（轉接器不能改）；成員不存在時回傳 False。"""
    if not changes:
        return get(connection, member_id) is not None
    if not set(changes) <= EDITABLE:
        raise ValueError('不能修改的欄位')
    columns = sorted(changes)
    assignments = ', '.join('%s = ?' % column for column in columns)
    values = [int(changes[c]) if c == 'enabled' else changes[c] for c in columns]
    return bool(connection.execute('UPDATE members SET %s, updated = ? WHERE id = ?' % assignments,
                                   (*values, now, member_id)).rowcount)


def delete(connection: sqlite3.Connection, member_id: str, now: float) -> bool:
    """刪除成員設定，保留它的對話（回合記著當時的名稱）；還有進行中回合時丟 MemberBusy。

    新增成員的請求登記保留並標為 deleted：刪除後用同一個請求 ID 重送會明確告知已刪除，不重新新增（NFR-1）。
    """
    connection.execute('BEGIN IMMEDIATE')
    try:
        if get(connection, member_id) is None:
            connection.execute('COMMIT')
            return False
        if connection.execute('SELECT 1 FROM turns WHERE member = ? AND state = ?',
                              (member_id, turns.RUNNING)).fetchone():
            raise MemberBusy('這位成員還有進行中的回合')
        connection.execute('DELETE FROM members WHERE id = ?', (member_id,))
        connection.execute('UPDATE requests SET state = ?, result = NULL, updated = ? WHERE id = ?',
                           ('deleted', now, member_id))
        connection.execute('COMMIT')
    except BaseException:
        connection.execute('ROLLBACK')
        raise
    return True


def status(connection: sqlite3.Connection, member_id: str) -> str:
    """FR-1：有進行中回合＝執行中；否則最近一個回合是未知＝需要人核對；其他＝閒置。"""
    if connection.execute('SELECT 1 FROM turns WHERE member = ? AND state = ?',
                          (member_id, turns.RUNNING)).fetchone():
        return RUNNING
    latest = connection.execute('SELECT state FROM turns WHERE member = ? ORDER BY started DESC, rowid DESC LIMIT 1',
                                (member_id,)).fetchone()
    return NEEDS_REVIEW if latest is not None and latest['state'] == turns.UNKNOWN else IDLE
