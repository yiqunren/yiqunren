"""調度員辦公室現況快照的共用契約；App 與主機橋接都 import，只含驗證，不讀任何資料。

快照只含伺服器設定與橋接公開額度欄位，是提出建議當下的資料，
不是授權、保留額度或啟用狀態的保證。
"""
from __future__ import annotations

import json
import math
import re
from datetime import datetime

from app.services import adapters
from app.services.consultants.profiles import PROFILES

VERSION = 1
MAX_BYTES = 1500
LOW_PERCENT = 10  # 與群聊已部署的週額度門檻相同
STATUSES = ("ok", "low", "unknown")
MODEL_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,103}")
EFFORT_ID = re.compile(r"[A-Za-z0-9._-]{1,40}")


def _timestamp(value: object) -> bool:
    if not isinstance(value, str) or len(value) > 40:
        return False
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return False
    return moment.tzinfo is not None


def _check_weekly(weekly: object) -> None:
    if not isinstance(weekly, dict) or set(weekly) != {"status", "remaining_percent", "resets_at"}:
        raise ValueError("調度現況額度欄位無效")
    status, remaining, reset = weekly["status"], weekly["remaining_percent"], weekly["resets_at"]
    if status not in STATUSES:
        raise ValueError("調度現況額度狀態無效")
    if status == "unknown":
        if remaining is not None or reset is not None:
            raise ValueError("未知額度不能附帶數值")
        return
    if (type(remaining) not in (int, float) or not math.isfinite(remaining) or not 0 <= remaining <= 100
            or (remaining < LOW_PERCENT) != (status == "low")
            or (reset is not None and not _timestamp(reset))):
        raise ValueError("調度現況額度數值無效")


def validate_context(value: object) -> dict:
    """嚴格檢查快照形狀；不接受額外欄位、未知顧問或可夾帶指令的字串。"""
    if not isinstance(value, dict) or set(value) != {"v", "as_of", "workers", "consultants"}:
        raise ValueError("調度現況欄位無效")
    if type(value["v"]) is not int or value["v"] != VERSION or not _timestamp(value["as_of"]):
        raise ValueError("調度現況版本或時間無效")
    workers = value["workers"]
    # 工作者＝轉接器登記處目前登記的每一家；多一家、少一家都拒絕。
    if not isinstance(workers, dict) or set(workers) != set(adapters.codes()):
        raise ValueError("調度現況工作者無效")
    for row in workers.values():
        if (not isinstance(row, dict) or set(row) != {"model", "effort", "configured", "weekly"}
                or not isinstance(row["model"], str) or not isinstance(row["effort"], str)
                or (row["model"] and not MODEL_ID.fullmatch(row["model"]))
                or (row["effort"] and not EFFORT_ID.fullmatch(row["effort"]))
                or type(row["configured"]) is not bool):
            raise ValueError("調度現況工作者設定無效")
        _check_weekly(row["weekly"])
    consultants = value["consultants"]
    if not isinstance(consultants, dict) or set(consultants) != {"enabled", "disabled", "unknown"}:
        raise ValueError("調度現況顧問欄位無效")
    seen = []
    for group in consultants.values():
        if not isinstance(group, list) or any(not isinstance(slug, str) or slug not in PROFILES for slug in group):
            raise ValueError("調度現況顧問代號無效")
        seen.extend(group)
    if len(seen) != len(set(seen)) or set(seen) != set(PROFILES):
        raise ValueError("調度現況須完整且不重複列出每位顧問")
    if len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()) > MAX_BYTES:
        raise ValueError("調度現況過長")
    return value
