"""本機狀態資料庫：SQLite（標準庫 sqlite3）、WAL 模式，資料表版本用 PRAGMA user_version 管理。

不存提示詞全文或憑證（NFR-4、NFR-6）。資料庫目錄只給擁有者存取（0700），檔案 0600。
"""
from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import stat


DB_NAME = 'state.sqlite3'

# 第 n 個元素把資料庫從版本 n 升到 n+1；已發布的元素不再修改，只往後加。
MIGRATIONS: tuple[tuple[str, ...], ...] = (
    (
        'CREATE TABLE requests ('
        ' id TEXT PRIMARY KEY,'
        ' kind TEXT NOT NULL,'
        ' payload_hash TEXT NOT NULL,'
        ' state TEXT NOT NULL,'
        ' created REAL NOT NULL,'
        ' updated REAL NOT NULL,'
        ' result TEXT'
        ')',
    ),
    (
        # FR-2 私聊回合；id 就是送出時的請求 ID。不存使用者訊息全文。
        'CREATE TABLE turns ('
        ' id TEXT PRIMARY KEY REFERENCES requests(id),'
        ' conversation_id TEXT NOT NULL,'
        ' member TEXT NOT NULL,'
        ' state TEXT NOT NULL,'
        ' error_kind TEXT,'
        ' reply TEXT,'
        ' started REAL NOT NULL,'
        ' finished REAL'
        ')',
        # 同一段對話同時只能有一個進行中的回合。
        "CREATE UNIQUE INDEX turns_one_running ON turns(conversation_id) WHERE state = 'running'",
        'CREATE TABLE turn_events ('
        ' turn_id TEXT NOT NULL REFERENCES turns(id),'
        ' seq INTEGER NOT NULL,'
        ' kind TEXT NOT NULL,'
        ' data TEXT NOT NULL,'
        ' created REAL NOT NULL,'
        ' PRIMARY KEY (turn_id, seq)'
        ')',
    ),
    (
        # FR-2：擁有者送出的訊息全文存在本機（第 2 版之前的回合沒有存，值為 NULL）。
        'ALTER TABLE turns ADD COLUMN message TEXT',
        'CREATE INDEX turns_conversation ON turns(conversation_id, started)',
    ),
    (
        # 轉接器接受回合後存下的身分（JSON），伺服器重啟後用來接回；不含訊息、回覆或憑證。
        'ALTER TABLE turns ADD COLUMN bridge_record TEXT',
    ),
    (
        # FR-1 成員設定；id 就是新增時的請求 ID。不存憑證（NFR-4）。timeout 是秒數。
        'CREATE TABLE members ('
        ' id TEXT PRIMARY KEY REFERENCES requests(id),'
        ' adapter TEXT NOT NULL,'
        ' name TEXT NOT NULL,'
        ' model TEXT NOT NULL,'
        ' effort TEXT,'
        ' auth_mode TEXT NOT NULL,'
        ' timeout INTEGER NOT NULL,'
        ' enabled INTEGER NOT NULL,'
        ' created REAL NOT NULL,'
        ' updated REAL NOT NULL'
        ')',
        # 回合記下當時的成員名稱與轉接器：成員刪除後對話照樣看得懂，重啟接回時找得到執行者。
        'ALTER TABLE turns ADD COLUMN member_name TEXT',
        'ALTER TABLE turns ADD COLUMN adapter TEXT',
        'CREATE INDEX turns_member ON turns(member, started)',
    ),
    (
        # NFR-3 配對：同時只有一組有效的配對碼（只存雜湊）；已配對的瀏覽器只存憑證的雜湊。
        'CREATE TABLE pairing_code ('
        ' id INTEGER PRIMARY KEY CHECK (id = 1),'
        ' code_hash TEXT NOT NULL,'
        ' expires REAL NOT NULL,'
        ' failures INTEGER NOT NULL'
        ')',
        'CREATE TABLE browser_sessions ('
        ' token_hash TEXT PRIMARY KEY,'
        ' created REAL NOT NULL,'
        ' last_used REAL NOT NULL'
        ')',
    ),
    (
        # NFR-7：轉接器那一家的對話身分（例如 Claude Code 的 session ID），只在完成的回合存，供下一個回合續接。
        'ALTER TABLE turns ADD COLUMN provider_session TEXT',
    ),
)
SCHEMA_VERSION = len(MIGRATIONS)


class StorageError(RuntimeError):
    pass


def database_path(state_dir: Path) -> Path:
    return Path(state_dir) / DB_NAME


def connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(path), timeout=5, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    # 刪除時用零覆寫舊內容，擁有者刪掉的對話不留在資料庫檔的空白頁裡（FR-2）。
    connection.execute('PRAGMA secure_delete = ON')
    return connection


def truncate_wal(connection: sqlite3.Connection) -> bool:
    """把 WAL 寫回主檔並清空；有其他連線正在讀時可能做不完整，回傳是否完整完成。"""
    busy, _, _ = connection.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()
    return busy == 0


def schema_version(connection: sqlite3.Connection) -> int:
    return connection.execute('PRAGMA user_version').fetchone()[0]


def migrate(connection: sqlite3.Connection, *, on_create=None) -> int:
    """on_create(connection) 只在資料庫第一次建立（原本版本是 0）時、於建表的同一個交易裡呼叫；
    它丟出例外時整個建立一起撤銷，下次再試。從舊版本升級時不呼叫。"""
    connection.execute('BEGIN IMMEDIATE')
    try:
        current = schema_version(connection)
        if current > SCHEMA_VERSION:
            raise StorageError('資料庫版本比程式新，請改用較新版本的程式')
        for version in range(current, SCHEMA_VERSION):
            for statement in MIGRATIONS[version]:
                connection.execute(statement)
            connection.execute('PRAGMA user_version = %d' % (version + 1))
        if current == 0 and on_create is not None:
            on_create(connection)
        connection.execute('COMMIT')
    except BaseException:
        connection.execute('ROLLBACK')
        raise
    return SCHEMA_VERSION


def _check_private_dir(path: Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = os.lstat(path)
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise StorageError('狀態目錄必須是擁有者自己的目錄，權限 0700')


def _check_private_file(path: Path) -> None:
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
            raise StorageError('資料庫檔必須是擁有者自己的一般檔案，權限 0600')
    finally:
        os.close(fd)


def prepare(state_dir: Path, *, on_create=None) -> Path:
    """建立或升級資料庫，回傳資料庫路徑。失敗時丟 StorageError，不默默改用其他位置。
    on_create 見 migrate：只在第一次建立時呼叫（例如建立預設成員）。"""
    state_dir = Path(state_dir)
    if not state_dir.is_absolute():
        raise StorageError('狀態目錄必須是絕對路徑')
    path = database_path(state_dir)
    try:
        _check_private_dir(state_dir)
        _check_private_file(path)
        connection = connect(path)
        try:
            mode = connection.execute('PRAGMA journal_mode=WAL').fetchone()[0]
            if mode != 'wal':
                raise StorageError('無法啟用 WAL 模式')
            migrate(connection, on_create=on_create)
        finally:
            connection.close()
    except StorageError:
        raise
    except (OSError, sqlite3.Error) as exc:
        raise StorageError('狀態資料庫無法開啟') from exc
    return path
