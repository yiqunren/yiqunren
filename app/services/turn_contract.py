"""非同步工作者回合的共用契約（App 與主機橋接都 import）；不執行命令、不存取主機路徑。

一個回合＝一次私聊或派工工作者的 CLI 執行。橋接收到 turn_begin 後立即回覆，CLI 在主機端繼續跑；
App 以 turn_status 查回、turn_stop 中斷、turn_ack 在存檔後讓橋接丟掉回覆全文。
"""
from __future__ import annotations

import hashlib
import json
from uuid import UUID

from app.services import adapters

# 2：turn_begin 加上 auth_mode（FR-1 認證模式），fields 依模式而定。
TURN_PROTOCOL = 2
ACTION_BEGIN = "turn_begin"
ACTION_STATUS = "turn_status"
ACTION_STOP = "turn_stop"
ACTION_ACK = "turn_ack"
CONTROL_ACTIONS = (ACTION_STATUS, ACTION_STOP, ACTION_ACK)

# 提供者（轉接器）清單、各自支援的認證模式與 turn_begin 的 fields 欄位都由轉接器登記處提供（app/services/adapters.py）。

# 單回合逾時：每位工作者的設定（秒）。預設 15 分鐘、上限 60 分鐘；橋接可用環境變數再壓低上限。
TIMEOUT_MIN = 60
TIMEOUT_MAX = 3600
TIMEOUT_DEFAULT = 900

STATES = ("running", "stopping", "done", "failed", "stopped", "unknown")
TERMINAL = frozenset({"done", "failed", "stopped", "unknown"})
# 主機回報 unknown 時的固定原因；App 只顯示對應的中文，不顯示主機原文。
UNKNOWN_REASONS = frozenset({"bridge_restarted", "stop_unconfirmed", "bridge_stopping"})

MAX_PROGRESS_BATCH = 50
MAX_ERROR_CHARS = 500
PROGRESS_KEYS = frozenset({"kind", "event", "item_type", "completed", "elapsed"})


def fingerprint(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def call_hash(packet: dict) -> str:
    return fingerprint({key: value for key, value in packet.items() if key != "call_hash"})


def request_id(value) -> str:
    if not isinstance(value, str):
        raise ValueError("回合識別無效")
    try:
        valid = str(UUID(value)) == value
    except (ValueError, AttributeError):
        valid = False
    if not valid:
        raise ValueError("回合識別無效")
    return value


def timeout_seconds(value, maximum: int = TIMEOUT_MAX) -> int:
    if type(value) is not int or not TIMEOUT_MIN <= value <= maximum:
        raise ValueError(f"單回合逾時必須是 {TIMEOUT_MIN}～{maximum} 秒的整數")
    return value


def begin_packet(provider: str, key: str, fields: dict, timeout: int, *, auth_mode: str) -> dict:
    packet = {"action": ACTION_BEGIN, "protocol": TURN_PROTOCOL, "provider": provider, "auth_mode": auth_mode,
              "request_id": key, "timeout": timeout, "fields": dict(fields)}
    packet["call_hash"] = call_hash(packet)
    return validate_begin(packet, provider)


def validate_begin(packet, provider: str, maximum: int = TIMEOUT_MAX) -> dict:
    keys = {"action", "protocol", "provider", "auth_mode", "request_id", "timeout", "fields", "call_hash"}
    if not isinstance(packet, dict) or set(packet) != keys or packet["action"] != ACTION_BEGIN:
        raise ValueError("回合封包欄位無效")
    if (packet["protocol"] != TURN_PROTOCOL or packet["provider"] != provider
            or not adapters.is_registered(provider)):
        raise ValueError("回合封包版本或提供者不符")
    adapter = adapters.get(provider)
    if not isinstance(packet["auth_mode"], str) or packet["auth_mode"] not in adapter.auth_modes:
        raise ValueError("回合封包認證模式不符")
    request_id(packet["request_id"])
    timeout_seconds(packet["timeout"], maximum)
    if not isinstance(packet["fields"], dict) or set(packet["fields"]) != adapter.fields_for(packet["auth_mode"]):
        raise ValueError("回合封包欄位無效")
    if packet["call_hash"] != call_hash(packet):
        raise ValueError("回合封包指紋不符")
    return packet


def control_packet(action: str, begin: dict, epoch: str, since: int = 0) -> dict:
    packet = {"action": action, "request_id": begin["request_id"], "call_hash": begin["call_hash"],
              "epoch": epoch}
    if action == ACTION_STATUS:
        packet["since"] = since
    return validate_control(packet)


def validate_control(packet) -> dict:
    if not isinstance(packet, dict) or packet.get("action") not in CONTROL_ACTIONS:
        raise ValueError("回合控制動作無效")
    keys = {"action", "request_id", "call_hash", "epoch"} | ({"since"} if packet["action"] == ACTION_STATUS else set())
    if set(packet) != keys:
        raise ValueError("回合控制欄位無效")
    request_id(packet["request_id"])
    request_id(packet["epoch"])
    if not isinstance(packet["call_hash"], str) or len(packet["call_hash"]) != 64:
        raise ValueError("回合控制指紋無效")
    if packet["action"] == ACTION_STATUS and (type(packet["since"]) is not int or packet["since"] < 0):
        raise ValueError("進度序號無效")
    return packet


def public_progress(item) -> dict | None:
    """只留固定欄位；格式不對就丟棄（進度只是顯示，不影響回合）。"""
    if not isinstance(item, dict) or not set(item) <= PROGRESS_KEYS:
        return None
    if item.get("kind") not in ("turn", "item") or item.get("event") not in ("started", "completed"):
        return None
    if "item_type" in item and (not isinstance(item["item_type"], str) or not 0 < len(item["item_type"]) <= 40):
        return None
    for key in ("completed", "elapsed"):
        if key in item and (type(item[key]) is not int or item[key] < 0):
            return None
    return dict(item)


def validate_reply(response, packet: dict) -> tuple[str, dict]:
    """核對主機回覆屬於這個回合；回傳 (epoch, turn)。結果正文由各提供者的用戶端再驗。"""
    if not isinstance(response, dict) or response.get("ok") is not True:
        raise ValueError("回合橋接回覆無效")
    epoch, turn = response.get("epoch"), response.get("turn")
    request_id(epoch)
    keys = {"request_id", "call_hash", "state", "error", "elapsed", "progress_seq", "progress", "result"}
    if not isinstance(turn, dict) or set(turn) != keys:
        raise ValueError("回合橋接回覆欄位無效")
    if turn["request_id"] != packet["request_id"] or turn["call_hash"] != packet["call_hash"]:
        raise ValueError("回合橋接回覆與原請求不符")
    if turn["state"] not in STATES:
        raise ValueError("回合狀態無效")
    if turn["error"] is not None and (not isinstance(turn["error"], str) or len(turn["error"]) > MAX_ERROR_CHARS):
        raise ValueError("回合錯誤欄位無效")
    if turn["state"] == "unknown" and turn["error"] not in UNKNOWN_REASONS:
        raise ValueError("回合未知原因無效")
    for key in ("elapsed", "progress_seq"):
        if type(turn[key]) is not int or turn[key] < 0:
            raise ValueError("回合計數欄位無效")
    if not isinstance(turn["progress"], list) or len(turn["progress"]) > MAX_PROGRESS_BATCH:
        raise ValueError("回合進度欄位無效")
    for entry in turn["progress"]:
        if (not isinstance(entry, dict) or set(entry) != {"seq", "item"} or type(entry["seq"]) is not int
                or not 0 < entry["seq"] <= turn["progress_seq"]):
            raise ValueError("回合進度欄位無效")
    if turn["state"] == "done" and turn["result"] is not None:
        # done 而 result 為 None：回覆已被 turn_ack 取走（App 已存檔），由呼叫端判斷。
        if not isinstance(turn["result"], dict) or not isinstance(turn["result"].get("content"), str):
            raise ValueError("回合結果無效")
    elif turn["state"] != "done" and turn["result"] is not None:
        raise ValueError("回合結果無效")
    return epoch, turn
