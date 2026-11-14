"""FR-2 私聊回合的狀態與事件。

資料庫是唯一的狀態來源：網頁重新整理時由這裡重送完整事件，不依賴瀏覽器的 Last-Event-ID。
擁有者的訊息與回覆存在本機，保留到擁有者刪除整段對話（FR-2、NFR-4）；不寫進 log（NFR-6）。
錯誤只存固定分類，不存原始錯誤訊息。
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
TIMEOUT = 'timeout'  # 超過單回合逾時，且已確認程序停止
REPLY_TOO_LONG = 'reply_too_long'  # 回覆超過長度上限，回覆不存（FR-2）
ERROR_KINDS = frozenset({INTERNAL_ERROR, TIMEOUT, REPLY_TOO_LONG})

PROGRESS = 'progress'
STOPPING = 'stopping'  # 中斷要求已送達轉接器，等它確認程序停止
DONE = 'done'


class ConversationBusy(RuntimeError):
    pass


class ConversationMemberMismatch(RuntimeError):
    """這段對話屬於另一位成員（FR-2：一段對話只屬於一位成員）。"""


TITLE_CHARS = 60  # 對話清單裡第一則訊息的開頭，最多幾個字


def insert_running(connection: sqlite3.Connection, turn_id: str, conversation_id: str, member: str,
                   message: str, now: float, *, member_name: str | None = None, adapter: str | None = None) -> None:
    """必須在呼叫者的交易裡執行（requests.claim 的 on_claim）。member 是成員 ID；
    member_name、adapter 是當時的成員名稱與轉接器（成員刪除後對話照樣看得懂，重啟接回時找得到執行者）。"""
    other = connection.execute('SELECT 1 FROM turns WHERE conversation_id = ? AND member != ? LIMIT 1',
                               (conversation_id, member)).fetchone()
    if other:
        raise ConversationMemberMismatch('這段對話屬於另一位成員')
    busy = connection.execute('SELECT 1 FROM turns WHERE conversation_id = ? AND state = ?',
                              (conversation_id, RUNNING)).fetchone()
    if busy:
        raise ConversationBusy('這段對話還有進行中的回合')
    try:
        connection.execute('INSERT INTO turns (id, conversation_id, member, member_name, adapter, message, state,'
                           ' started) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                           (turn_id, conversation_id, member, member_name, adapter, message, RUNNING, now))
    except sqlite3.IntegrityError as exc:
        raise ConversationBusy('這段對話還有進行中的回合') from exc


def get(connection: sqlite3.Connection, turn_id: str) -> sqlite3.Row | None:
    return connection.execute('SELECT * FROM turns WHERE id = ?', (turn_id,)).fetchone()


def conversation(connection: sqlite3.Connection, conversation_id: str) -> list[sqlite3.Row]:
    return connection.execute('SELECT * FROM turns WHERE conversation_id = ? ORDER BY started, rowid',
                              (conversation_id,)).fetchall()


def conversations(connection: sqlite3.Connection) -> list[dict]:
    """所有對話的摘要，最近有活動的排前面。成員與狀態取自最後一個回合，標題取自第一則訊息的開頭。"""
    rows = connection.execute('SELECT conversation_id, member, member_name, state, started, finished,'
                              ' substr(message, 1, ?) AS head, length(message) AS size'
                              ' FROM turns ORDER BY started, rowid', (TITLE_CHARS * 4,))
    found: dict[str, dict] = {}
    for row in rows:
        item = found.get(row['conversation_id'])
        if item is None:
            head = row['head'] or ''
            words = ' '.join(head.split())  # 換行與連續空白併成一個空白
            cut = len(words) > TITLE_CHARS or (row['size'] or 0) > len(head)
            title = words[:TITLE_CHARS] + ('…' if cut else '')
            item = found[row['conversation_id']] = {'id': row['conversation_id'], 'title': title, 'turns': 0}
        item['turns'] += 1
        item['member'], item['member_name'], item['state'] = row['member'], row['member_name'], row['state']
        item['updated'] = row['finished'] if row['finished'] is not None else row['started']
    return sorted(found.values(), key=lambda item: item['updated'], reverse=True)


def delete_conversation(connection: sqlite3.Connection, conversation_id: str, now: float) -> int:
    """刪除一整段對話的訊息、回覆與事件，回傳刪掉的回合數；還有進行中的回合時丟 ConversationBusy。

    請求登記（只有內容雜湊，沒有內容）保留並標為 deleted，讓刪除後用同一個請求 ID 重送時
    明確告知已刪除，而不是重新執行一次（NFR-1）。
    """
    connection.execute('BEGIN IMMEDIATE')
    try:
        states = [row['state'] for row in
                  connection.execute('SELECT state FROM turns WHERE conversation_id = ?', (conversation_id,))]
        if RUNNING in states:
            raise ConversationBusy('這段對話還有進行中的回合')
        if states:
            in_conversation = '(SELECT id FROM turns WHERE conversation_id = ?)'
            connection.execute('UPDATE requests SET state = ?, result = NULL, updated = ? WHERE id IN '
                               + in_conversation, ('deleted', now, conversation_id))
            connection.execute('DELETE FROM turn_events WHERE turn_id IN ' + in_conversation, (conversation_id,))
            connection.execute('DELETE FROM turns WHERE conversation_id = ?', (conversation_id,))
        connection.execute('COMMIT')
    except BaseException:
        connection.execute('ROLLBACK')
        raise
    return len(states)


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


def mark_stopping(connection: sqlite3.Connection, turn_id: str, now: float) -> int | None:
    """寫入「中斷中」事件；回合已結束或已經寫過時不再寫入，回傳 None。"""
    connection.execute('BEGIN IMMEDIATE')
    try:
        row = get(connection, turn_id)
        seen = connection.execute('SELECT 1 FROM turn_events WHERE turn_id = ? AND kind = ?',
                                  (turn_id, STOPPING)).fetchone()
        seq = (_append(connection, turn_id, STOPPING, {}, now)
               if row and row['state'] == RUNNING and not seen else None)
        connection.execute('COMMIT')
    except BaseException:
        connection.execute('ROLLBACK')
        raise
    return seq


def save_record(connection: sqlite3.Connection, turn_id: str, record: dict) -> bool:
    """存下轉接器接受回合後的身分（重啟後接回用）；回合不是進行中時不存，回傳 False。"""
    text = json.dumps(record, ensure_ascii=False, allow_nan=False, sort_keys=True)
    return bool(connection.execute('UPDATE turns SET bridge_record = ? WHERE id = ? AND state = ?',
                                   (text, turn_id, RUNNING)).rowcount)


def recorded_running(connection: sqlite3.Connection) -> list[tuple[str, str, str | None]]:
    """進行中、而且有轉接器身分的回合：(回合 ID, 身分 JSON, 轉接器代號)。"""
    return [(row['id'], row['bridge_record'], row['adapter']) for row in connection.execute(
        'SELECT id, bridge_record, adapter FROM turns WHERE state = ? AND bridge_record IS NOT NULL'
        ' ORDER BY started, rowid', (RUNNING,))]


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


def mark_running_unknown(connection: sqlite3.Connection, now: float, *, keep_recorded: bool = False) -> list[str]:
    """伺服器啟動時呼叫：上次執行留下、查不回結果的進行中回合標為未知（FR-2）。

    keep_recorded=True 時跳過有轉接器身分的回合，留給呼叫端接回。
    """
    query = 'SELECT id FROM turns WHERE state = ?' + (' AND bridge_record IS NULL' if keep_recorded else '')
    connection.execute('BEGIN IMMEDIATE')
    try:
        ids = [row['id'] for row in connection.execute(query, (RUNNING,))]
        for turn_id in ids:
            _finish_in_transaction(connection, turn_id, UNKNOWN, now, None, None)
        connection.execute('COMMIT')
    except BaseException:
        connection.execute('ROLLBACK')
        raise
    return ids
