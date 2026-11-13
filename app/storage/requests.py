"""NFR-1：請求登記與唯一執行權。

呼叫模型之前先登記請求：同 ID 同內容重送回傳原紀錄，同 ID 不同內容一律拒絕，
同一個 ID 只會有一個呼叫者拿到執行權。只存內容的雜湊，不存內容本身。
"""
from __future__ import annotations

from dataclasses import dataclass
import sqlite3
import time

from app.services.turn_contract import fingerprint, request_id as checked_request_id


CLAIMED = 'claimed'      # 這次呼叫取得執行權
EXISTING = 'existing'    # 同 ID 同內容，回傳原紀錄，不重複執行
REJECTED = 'rejected'    # 同 ID 不同內容


@dataclass(frozen=True)
class Claim:
    outcome: str
    state: str
    result: str | None


def claim(connection: sqlite3.Connection, request_id: str, kind: str, payload, *, clock=time.time,
          on_claim=None) -> Claim:
    """on_claim(connection, now) 只在這次取得執行權時、於同一個交易裡呼叫；它丟出例外時整筆登記一起撤銷。"""
    checked_request_id(request_id)
    if not isinstance(kind, str) or not kind:
        raise ValueError('請求類別無效')
    digest = fingerprint(payload)
    now = clock()
    connection.execute('BEGIN IMMEDIATE')
    try:
        row = connection.execute('SELECT kind, payload_hash, state, result FROM requests WHERE id = ?',
                                 (request_id,)).fetchone()
        if row is None:
            connection.execute('INSERT INTO requests (id, kind, payload_hash, state, created, updated)'
                               ' VALUES (?, ?, ?, ?, ?, ?)', (request_id, kind, digest, CLAIMED, now, now))
            if on_claim is not None:
                on_claim(connection, now)
            outcome, state, result = CLAIMED, CLAIMED, None
        elif row['kind'] == kind and row['payload_hash'] == digest:
            outcome, state, result = EXISTING, row['state'], row['result']
        else:
            outcome, state, result = REJECTED, row['state'], None
        connection.execute('COMMIT')
    except BaseException:
        connection.execute('ROLLBACK')
        raise
    return Claim(outcome, state, result)
