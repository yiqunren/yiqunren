"""WSL 群聊橋接：接受、封閉與自有程序生命週期，和私人 CLI 路徑分開。"""
from __future__ import annotations

import asyncio
import json
import os
import signal
import tempfile
import time
from pathlib import Path
from uuid import uuid4

from app.services.discussion_contract import (MAX_REPLY, DiscussionDiagnosticError, receipt_shape,
                                             safe_diagnostic, validate_begin, valid_id)
from scripts import host_diagnostics

START_TIMEOUT = 10
EXECUTION_TIMEOUT = 180
TERMINATE_GRACE = 5
OUTPUT_LIMIT = 2_000_000
# 固定診斷代碼對應主機診斷檔的 reason；其餘由事件守門拋出的代碼（cli_error_event 等）記為 event_rejected。
DIAG_REASONS = {"execution_timeout": "timeout", "cli_exit_nonzero": "exit_nonzero",
                "reply_parse_failed": "parse_failed", "reply_invalid": "parse_failed",
                "stdout_limit": "oversize", "stderr_limit": "oversize"}


def keep_tail(buffer: bytearray, data: bytes) -> None:
    """只保留最後 64 KiB，供失敗時的主機診斷檔使用；不經 socket 回傳。"""
    buffer.extend(data)
    if len(buffer) > host_diagnostics.TAIL_LIMIT:
        del buffer[:-host_diagnostics.TAIL_LIMIT]


def process_stat(pid: int) -> dict:
    # 只讀程序身分欄位；不讀 cmdline、環境、認證或日誌。
    path = Path(f"/proc/{pid}/stat")
    fields = path.read_text().rsplit(")", 1)[1].split()
    return {"pid": pid, "state": fields[0], "pgid": int(fields[2]), "sid": int(fields[3]),
            "start_ticks": int(fields[19]), "uid": path.stat().st_uid}


def birth_receipt(pid: int) -> dict:
    receipt = process_stat(pid)
    # 殭屍的 /proc 擁有者會變成 root；領頭程序已結束，視同程序已消失，不算歸屬不符。
    if receipt["state"] in ("Z", "X"):
        raise ProcessLookupError(pid)
    if receipt["pgid"] != pid or receipt["sid"] != pid or receipt["uid"] != os.getuid():
        raise RuntimeError("無法確認討論程序群組歸屬")
    receipt.pop("state")
    receipt["boot_id"] = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    return receipt


def validate_receipt(receipt: dict) -> None:
    receipt_shape(receipt)
    if receipt["uid"] != os.getuid():
        raise ValueError("程序收據無效")


def group_ended(receipt: dict) -> bool:
    validate_receipt(receipt)
    boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    if boot != receipt["boot_id"]:
        return True
    # PID 消失本身不足；核對整個自有群組。讀取不完整時不提供結束證據。
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            member = process_stat(int(entry.name))
        except FileNotFoundError:
            continue
        except (OSError, ValueError, IndexError):
            return False
        if member["pgid"] == receipt["pgid"] and member["sid"] == receipt["sid"] and member["state"] not in ("Z", "X"):
            return False
    return True


def signal_owned(receipt: dict) -> bool:
    validate_receipt(receipt)
    if receipt["boot_id"] != Path("/proc/sys/kernel/random/boot_id").read_text().strip():
        return False
    try:
        current = process_stat(receipt["pid"])
        if any(current[k] != receipt[k] for k in ("pid", "pgid", "sid", "start_ticks", "uid")):
            return False
        os.killpg(receipt["pgid"], signal.SIGTERM)
        return True
    except (FileNotFoundError, ProcessLookupError):
        return False
