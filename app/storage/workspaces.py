"""每段對話的工作目錄（SPEC NFR-7）：放在狀態目錄的 workspaces/ 底下，目錄名稱是對話 ID。

後端算出路徑交給轉接器；需要工作目錄的橋接在第一次執行時建立（ensure），並用 check 核對收到的路徑；
刪除對話時後端用 remove 刪除整個目錄。所有目錄都只給擁有者存取（0700），不跟隨符號連結。
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import stat
import uuid


ROOT_NAME = 'workspaces'


class WorkspaceError(ValueError):
    pass


def root(state_dir: Path) -> Path:
    return Path(state_dir) / ROOT_NAME


def path(state_dir: Path, conversation_id: str) -> Path:
    """對話 ID 必須是 UUID，所以路徑一定落在 workspaces/ 底下的一層。"""
    return root(state_dir) / str(uuid.UUID(conversation_id))


def _private_dir(directory: Path) -> None:
    info = os.lstat(directory)
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o700):
        raise WorkspaceError('工作目錄必須是擁有者自己的目錄，權限 0700')


def check(workspace, root_dir: Path) -> Path:
    """核對 workspace 是 root_dir 底下以 UUID 命名、已存在的私人目錄（不是符號連結），回傳路徑。"""
    if not isinstance(workspace, str) or not workspace:
        raise WorkspaceError('工作目錄無效')
    candidate = Path(workspace)
    if not candidate.is_absolute() or candidate.parent != Path(root_dir):
        raise WorkspaceError('工作目錄不在允許的位置')
    try:
        uuid.UUID(candidate.name)
    except ValueError:
        raise WorkspaceError('工作目錄名稱無效') from None
    if candidate.name != str(uuid.UUID(candidate.name)):
        raise WorkspaceError('工作目錄名稱無效')
    try:
        _private_dir(Path(root_dir))
        _private_dir(candidate)
    except FileNotFoundError:
        raise WorkspaceError('工作目錄不存在') from None
    return candidate


def ensure(workspace, root_dir: Path) -> Path:
    """建立（已存在就沿用）並核對工作目錄。"""
    if not isinstance(workspace, str) or not Path(workspace).is_absolute() or Path(workspace).parent != Path(root_dir):
        raise WorkspaceError('工作目錄不在允許的位置')
    for directory in (Path(root_dir), Path(workspace)):
        try:
            directory.mkdir(mode=0o700)
        except FileExistsError:
            pass
    return check(workspace, root_dir)


def remove(state_dir: Path, conversation_id: str) -> bool:
    """刪除這段對話的工作目錄；不存在回傳 False。是符號連結或不是目錄時只拿掉那個項目本身，不跟過去。"""
    target = path(state_dir, conversation_id)
    try:
        info = os.lstat(target)
    except FileNotFoundError:
        return False
    if stat.S_ISDIR(info.st_mode):
        shutil.rmtree(target)  # rmtree 不跟隨目錄裡的符號連結
    else:
        target.unlink()
    return True
