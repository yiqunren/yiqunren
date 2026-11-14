"""NFR-3 配對碼與已配對瀏覽器的資料存取。

配對碼與瀏覽器憑證都只存 SHA-256 雜湊，不存原值。配對碼怎麼產生、Cookie 怎麼發，在 app/web/security.py。
"""
from __future__ import annotations

import hashlib
import hmac
import sqlite3


CODE_TTL = 600                  # 配對碼 10 分鐘內有效
CODE_MAX_FAILURES = 5           # 輸錯 5 次就作廢
SESSION_IDLE = 30 * 24 * 3600   # 連續 30 天沒使用就失效
TOUCH_INTERVAL = 600            # 最後使用時間最多每 10 分鐘寫回一次，不必每個請求都寫資料庫

PAIRED = 'paired'
WRONG = 'wrong'
NO_CODE = 'no_code'   # 沒有有效的配對碼：從沒產生、已用過、已過期或已作廢


def digest(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def issue_code(connection: sqlite3.Connection, code_hash: str, now: float) -> None:
    """存下新的配對碼；同時只有一組有效，舊的（含輸錯次數）一併作廢。"""
    connection.execute('INSERT OR REPLACE INTO pairing_code (id, code_hash, expires, failures) VALUES (1, ?, ?, 0)',
                       (code_hash, now + CODE_TTL))


def redeem(connection: sqlite3.Connection, code_hash: str, token_hash: str, now: float) -> str:
    """配對碼對了就作廢它並登記瀏覽器憑證（PAIRED）；錯了記一次失敗（WRONG），滿 5 次作廢。"""
    connection.execute('BEGIN IMMEDIATE')
    try:
        row = connection.execute('SELECT code_hash, expires, failures FROM pairing_code WHERE id = 1').fetchone()
        if row is None:
            outcome = NO_CODE
        elif row['expires'] <= now:
            connection.execute('DELETE FROM pairing_code')
            outcome = NO_CODE
        elif hmac.compare_digest(row['code_hash'], code_hash):
            connection.execute('DELETE FROM pairing_code')
            connection.execute('INSERT INTO browser_sessions (token_hash, created, last_used) VALUES (?, ?, ?)',
                               (token_hash, now, now))
            outcome = PAIRED
        else:
            if row['failures'] + 1 >= CODE_MAX_FAILURES:
                connection.execute('DELETE FROM pairing_code')
            else:
                connection.execute('UPDATE pairing_code SET failures = failures + 1')
            outcome = WRONG
        connection.execute('COMMIT')
    except BaseException:
        connection.execute('ROLLBACK')
        raise
    return outcome


def check_session(connection: sqlite3.Connection, token_hash: str, now: float) -> bool:
    """憑證有效就回傳 True，並視需要更新最後使用時間（續期）；超過 30 天沒使用的刪掉並回傳 False。"""
    row = connection.execute('SELECT last_used FROM browser_sessions WHERE token_hash = ?', (token_hash,)).fetchone()
    if row is None:
        return False
    if now - row['last_used'] > SESSION_IDLE:
        connection.execute('DELETE FROM browser_sessions WHERE token_hash = ?', (token_hash,))
        return False
    if now - row['last_used'] >= TOUCH_INTERVAL:
        connection.execute('UPDATE browser_sessions SET last_used = ? WHERE token_hash = ?', (now, token_hash))
    return True


def revoke(connection: sqlite3.Connection, token_hash: str) -> bool:
    return bool(connection.execute('DELETE FROM browser_sessions WHERE token_hash = ?', (token_hash,)).rowcount)


def revoke_all(connection: sqlite3.Connection) -> int:
    """撤銷所有已配對的瀏覽器，尚未使用的配對碼也作廢；回傳撤銷的瀏覽器數。"""
    connection.execute('BEGIN IMMEDIATE')
    try:
        count = connection.execute('DELETE FROM browser_sessions').rowcount
        connection.execute('DELETE FROM pairing_code')
        connection.execute('COMMIT')
    except BaseException:
        connection.execute('ROLLBACK')
        raise
    return count


def has_sessions(connection: sqlite3.Connection, now: float) -> bool:
    return connection.execute('SELECT 1 FROM browser_sessions WHERE last_used >= ? LIMIT 1',
                              (now - SESSION_IDLE,)).fetchone() is not None
