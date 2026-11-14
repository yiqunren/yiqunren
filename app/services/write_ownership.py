"""本機共用寫入權；只保存範圍與狀態，不保存工作內容或憑證。"""
from __future__ import annotations

from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import sqlite3
import stat
import time
import uuid

from app.web import config


# 預設放在狀態目錄（和後端資料庫同一個 0700 目錄），不放在 repo 底下：repo 可能 clone 在 WSL 的 /mnt/* 上。
REGISTRY_NAME = 'write-ownership.sqlite3'


class OwnershipError(RuntimeError):
    pass


def default_registry(env=None):
    try:
        return config.resolve_state_dir(env) / REGISTRY_NAME
    except config.ConfigError as exc:
        raise OwnershipError('找不到狀態目錄，禁止開始寫入') from exc


def configured_registry(env=None):
    """YIQUNREN_WRITE_REGISTRY 有設就用它，否則用狀態目錄裡的登記庫。"""
    env = os.environ if env is None else env
    override = env.get('YIQUNREN_WRITE_REGISTRY', '')
    return WriteRegistry(Path(override) if override else default_registry(env))


def _plain(value, label):
    if not isinstance(value, str) or not 1 <= len(value) <= 160 or any(ord(c) < 32 for c in value):
        raise OwnershipError(label + '格式不符')
    return value


def scope_paths(project, files):
    project = Path(project)
    if not project.is_absolute() or not project.is_dir() or project.resolve() != project:
        raise OwnershipError('專案必須是存在且未經符號連結轉向的絕對目錄')
    if not isinstance(files, list) or not 1 <= len(files) <= 128:
        raise OwnershipError('須提供一至 128 個相對檔案範圍')
    scopes = []
    for value in files:
        if not isinstance(value, str) or not value or len(value) > 1024:
            raise OwnershipError('檔案範圍格式不符')
        directory = value == '.' or value.endswith('/')
        path = Path(value)
        if path.is_absolute() or '..' in path.parts or any(c in value for c in '\\*?[]\x00\n\r'):
            raise OwnershipError('範圍不可包含逃逸路徑、萬用字元或控制字元')
        target = project / path
        if target.resolve() != target or not target.is_relative_to(project):
            raise OwnershipError('範圍不可經符號連結轉向')
        if target.is_dir() and not directory:
            raise OwnershipError('目錄範圍須以 / 結尾；整個專案使用 .')
        scope = {'path': str(target), 'directory': directory}
        if scope not in scopes:
            scopes.append(scope)
    return str(project), scopes


def overlaps(left, right):
    a, b = Path(left['path']), Path(right['path'])
    return a == b or (left['directory'] and b.is_relative_to(a)) or (right['directory'] and a.is_relative_to(b))


class WriteRegistry:
    def __init__(self, path, clock=time.time):
        self.path, self.clock = Path(path), clock

    @contextmanager
    def transaction(self):
        connection = None
        try:
            if not self.path.is_absolute() or self.path.resolve() != self.path:
                raise OwnershipError('登記庫路徑不安全，禁止開始寫入')
            self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            parent = self.path.parent.stat()
            if parent.st_uid != os.getuid() or stat.S_IMODE(parent.st_mode) != 0o700:
                raise OwnershipError('登記庫目錄權限不符，禁止開始寫入')
            fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            try:
                info = os.fstat(fd)
                if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
                    raise OwnershipError('登記庫權限不符，禁止開始寫入')
            finally:
                os.close(fd)
            connection = sqlite3.connect(str(self.path), timeout=3, isolation_level=None)
            connection.row_factory = sqlite3.Row
            connection.execute('BEGIN IMMEDIATE')
            connection.execute('CREATE TABLE IF NOT EXISTS leases (id TEXT PRIMARY KEY, project TEXT NOT NULL, '
                'files TEXT NOT NULL, holder TEXT NOT NULL, state TEXT NOT NULL, acquired REAL NOT NULL, '
                'updated REAL NOT NULL, expires REAL NOT NULL)')
            now = self.clock()
            if not isinstance(now, (int, float)) or not math.isfinite(now):
                raise OwnershipError('時鐘不可確認，禁止開始寫入')
            for row in connection.execute('SELECT * FROM leases'):
                scopes = json.loads(row['files'])
                if (row['state'] not in ('active', 'unknown', 'released') or not isinstance(scopes, list)
                        or not scopes or not isinstance(row['holder'], str) or not row['holder']
                        or not Path(row['project']).is_absolute()
                        or any(not isinstance(row[key], (int, float)) or not math.isfinite(row[key]) for key in ('acquired', 'updated', 'expires'))
                        or any(not isinstance(scope, dict) or set(scope) != {'path', 'directory'}
                            or not isinstance(scope['path'], str) or not Path(scope['path']).is_absolute()
                            or not Path(scope['path']).is_relative_to(row['project'])
                            or type(scope['directory']) is not bool for scope in scopes)):
                    raise OwnershipError('登記資料不可確認，禁止開始寫入')
            connection.execute("UPDATE leases SET state='unknown', updated=? WHERE state='active' AND (expires<=? OR updated>?)", (now, now, now))
            yield connection, now
            connection.commit()
        except OwnershipError:
            raise
        except (OSError, sqlite3.Error, ValueError, TypeError) as exc:
            raise OwnershipError('登記庫不可確認，禁止開始寫入') from exc
        finally:
            if connection is not None:
                connection.close()

    @staticmethod
    def record(row):
        return {'lease_id': row['id'], 'project': row['project'], 'files': json.loads(row['files']),
                'holder': row['holder'], 'state': row['state'], 'acquired_at': row['acquired'],
                'updated_at': row['updated'], 'expires_at': row['expires']}

    def claim(self, project, files, holder, ttl=300):
        holder = _plain(holder, '持有人')
        if type(ttl) is not int or not 1 <= ttl <= 3600:
            raise OwnershipError('有效期限須為一至 3600 秒')
        project, scopes = scope_paths(project, files)
        with self.transaction() as (db, now):
            rows = db.execute("SELECT * FROM leases WHERE state IN ('active','unknown')").fetchall()
            for row in rows:
                if any(overlaps(a, b) for a in scopes for b in json.loads(row['files'])):
                    raise OwnershipError('寫入範圍衝突或原持有人狀態未知：' + row['id'])
            identity = str(uuid.uuid4())
            db.execute('INSERT INTO leases VALUES (?,?,?,?,?,?,?,?)',
                (identity, project, json.dumps(scopes), holder, 'active', now, now, now + ttl))
            return self.record(db.execute('SELECT * FROM leases WHERE id=?', (identity,)).fetchone())

    def list(self):
        if not self.path.is_absolute() or self.path.resolve() != self.path:
            raise OwnershipError('登記庫路徑不安全，狀態不可確認')
        if not self.path.exists():
            if self.path.is_symlink():
                raise OwnershipError('登記庫路徑不安全')
            return []
        with self.transaction() as (db, _now):
            return [self.record(row) for row in db.execute("SELECT * FROM leases WHERE state IN ('active','unknown') ORDER BY acquired")]

    def change(self, identity, holder, action, ttl=300, stopped=False):
        holder = _plain(holder, '持有人')
        if action not in ('renew', 'release', 'unknown', 'resolve'):
            raise OwnershipError('未知登記操作')
        if type(ttl) is not int or not 1 <= ttl <= 3600:
            raise OwnershipError('有效期限須為一至 3600 秒')
        with self.transaction() as (db, now):
            row = db.execute('SELECT * FROM leases WHERE id=?', (identity,)).fetchone()
            if row is None or row['holder'] != holder:
                raise OwnershipError('登記不存在或持有人不符')
            if row['state'] not in ('active', 'unknown'):
                raise OwnershipError('登記已結束，不能重複操作')
            if action in ('release', 'renew') and row['state'] != 'active':
                raise OwnershipError('狀態未知時不可釋放或續期；須先確認原工作者已停止')
            if action == 'resolve' and stopped is not True:
                raise OwnershipError('人工解除須明示已確認原工作者停止')
            state = 'active' if action == 'renew' else 'unknown' if action == 'unknown' else 'released'
            db.execute('UPDATE leases SET state=?, updated=?, expires=? WHERE id=?',
                (state, now, now + ttl if action == 'renew' else row['expires'], identity))
            return self.record(db.execute('SELECT * FROM leases WHERE id=?', (identity,)).fetchone())


async def guarded_write(project, holder, operation, ttl=300):
    """申請成功才建立工作協程；任何未確認成功的結束均保留未知狀態。"""
    registry = configured_registry()
    lease = registry.claim(str(project), ['.'], holder, ttl)
    try:
        result = await operation()
        registry.change(lease['lease_id'], holder, 'release')
        return result
    except BaseException:
        registry.change(lease['lease_id'], holder, 'unknown')
        raise
