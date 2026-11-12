"""工作區指紋：判斷失敗的非同步回合有沒有動過工作區（scripts/turn_host.py 決定能否釋放寫入權）。

每個項目記相對路徑、類型、權限位元、大小、mtime_ns、inode；symlink 不跟隨，只記連結目標字串；
一般檔另記內容 SHA-256（大小與 mtime 被還原也抓得到）。
項目數（檔、目錄、連結都算）或一般檔總量超過上限、走訪或讀檔出錯，一律回傳 None，
代表「無法證明沒變」，呼叫端應維持 unknown。
"""
from __future__ import annotations

import hashlib
import os
import stat

MAX_ENTRIES = 2000
MAX_BYTES = 64 * 1024 * 1024
CHANGED_LIMIT = 50
_CHUNK = 1024 * 1024


def _digest(path: str) -> str:
    # O_NOFOLLOW：走訪後被換成 symlink 時不跟過去；O_NONBLOCK：被換成 FIFO 時不卡住。
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError("不是一般檔")
        digest, read = hashlib.sha256(), 0
        while chunk := os.read(fd, _CHUNK):
            read += len(chunk)
            if read > MAX_BYTES:
                raise OSError("讀檔時超過總量上限")
            digest.update(chunk)
        return digest.hexdigest()
    finally:
        os.close(fd)


def take(root) -> dict | None:
    """回傳 {相對路徑: [類型, 權限, 大小, mtime_ns, inode, 內容或連結目標]}；超過上限或出錯回傳 None。"""
    root = os.fspath(root)
    entries: dict[str, list] = {}
    files: list[str] = []
    total = 0
    pending = [""]
    try:
        while pending:
            relative = pending.pop()
            with os.scandir(os.path.join(root, relative) if relative else root) as listing:
                for entry in listing:
                    path = f"{relative}/{entry.name}" if relative else entry.name
                    info = entry.stat(follow_symlinks=False)
                    mode, extra = info.st_mode, None
                    if stat.S_ISDIR(mode):
                        kind = "dir"
                        pending.append(path)
                    elif stat.S_ISLNK(mode):
                        kind, extra = "link", os.readlink(entry.path)
                    elif stat.S_ISREG(mode):
                        kind = "file"
                        total += info.st_size
                        files.append(path)
                    else:
                        kind = "other"
                    entries[path] = [kind, stat.S_IMODE(mode), info.st_size, info.st_mtime_ns, info.st_ino, extra]
                    if len(entries) > MAX_ENTRIES or total > MAX_BYTES:
                        return None
        for path in files:
            entries[path][5] = _digest(os.path.join(root, path))
    except OSError:
        return None
    return entries


def diff(before: dict, after: dict) -> tuple[list[str], int]:
    """回傳（排序後最多 CHANGED_LIMIT 個有變動的相對路徑, 變動總數）；新增、刪除、任何欄位不同都算。"""
    changed = sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))
    return changed[:CHANGED_LIMIT], len(changed)
