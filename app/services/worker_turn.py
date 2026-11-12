"""App 端的非同步工作者回合：begin → 每 1.5 秒查回 → 交回結果；可中斷，App 重啟後可接回。

回合的身分、逾時、存檔回呼與中斷鍵由外圍的 `async with tracked(...)` 提供。
"""
from __future__ import annotations

import asyncio
import contextvars
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass

from app.services import adapters, cli_socket
from app.services import turn_contract as contract

logger = logging.getLogger(__name__)

POLL_SECONDS = 1.5
CONTROL_TIMEOUT = 15
TRANSPORT_RETRIES = 5
DEADLINE_GRACE = 120


def label(provider: object) -> str:
    """回合狀態與錯誤訊息裡的顯示名稱，取自轉接器登記處；未登記時只寫 worker，不帶入原值。"""
    return adapters.get(provider).name if adapters.is_registered(provider) else "worker"


INTERRUPTED_TEXT = "已中斷這一回合：工作者的程序已確認結束。工作區可能留有半套改動，續問前請先檢查。"
UNKNOWN_TEXT = {
    "bridge_restarted": "橋接曾重啟，這一回合的結果無法取得；工作者是否改過工作區未知，請先檢查。",
    "bridge_stopping": "橋接關閉時這一回合仍在執行，結果無法取得；請先檢查工作區。",
    "stop_unconfirmed": "已要求中斷，但無法確認工作者程序已結束；寫入權登記會標為未知，需人工核對。",
    "deadline": "超過時限仍未收到結束回報，結果未知；請先檢查工作區。",
    "transport": "連續查詢都連不上橋接，這一回合的結果未知；請確認橋接狀態。",
    "result_taken": "橋接回報已完成，但回覆已被取走；請重新整理查看是否已保存。",
}


class TurnInterrupted(RuntimeError):
    """使用者中斷，且橋接已確認程序群組結束。"""


class TurnUnknown(RuntimeError):
    def __init__(self, reason: str):
        super().__init__(UNKNOWN_TEXT.get(reason, UNKNOWN_TEXT["transport"]))
        self.reason = reason


@dataclass
class Handle:
    provider: str
    packet: dict
    epoch: str
    started_at: float
    stop_on_cancel: bool = False

    @property
    def timeout(self) -> int:
        return self.packet["timeout"]

    def record(self) -> dict:
        """存進資料庫的最小身分；不含回覆、進度或主機收據。"""
        return {"provider": self.provider, "request_id": self.packet["request_id"],
                "call_hash": self.packet["call_hash"], "epoch": self.epoch,
                "timeout": self.timeout, "started_at": self.started_at}

    @classmethod
    def from_record(cls, record: dict) -> "Handle":
        packet = {"request_id": contract.request_id(record["request_id"]), "call_hash": record["call_hash"],
                  "timeout": contract.timeout_seconds(record["timeout"])}
        if not adapters.is_registered(record.get("provider")):
            raise ValueError("回合紀錄的提供者無效")
        return cls(record["provider"], packet, contract.request_id(record["epoch"]), float(record["started_at"]))


@dataclass
class Track:
    key: str | None
    timeout: int
    on_begin: object = None
    stop_on_cancel: bool = False
    handle: Handle | None = None
    received: bool = False


TRACK: contextvars.ContextVar[Track | None] = contextvars.ContextVar("yiqunren_worker_turn", default=None)
# 中斷鍵 → 正在觀察中的回合；私聊為 "direct:<conversation_id>"，派工為 "dispatch:<conversation_id>:<proposal_id>"。
ACTIVE: dict[str, Handle] = {}


@asynccontextmanager
async def tracked(key: str | None, *, timeout: int = contract.TIMEOUT_DEFAULT, on_begin=None,
                  stop_on_cancel: bool = False):
    """on_begin(handle)：橋接接受後同步呼叫（在執行緒），用來把回合身分存進資料庫；失敗時立即中斷該回合。

    區塊正常結束（呼叫端已存好回覆）才 ack，讓橋接丟掉回覆全文；中途出錯則保留，App 重啟後還能取回。
    """
    track = Track(key, contract.timeout_seconds(timeout), on_begin, stop_on_cancel)
    token = TRACK.set(track)
    try:
        yield track
    except BaseException:
        raise
    else:
        if track.handle is not None and track.received:
            await ack(track.handle)
    finally:
        TRACK.reset(token)


def socket_path(provider: str) -> str:
    """橋接 socket 位置由轉接器登記處決定（可用環境變數覆寫）；未登記的提供者拋 ValueError。"""
    return adapters.socket_path(provider)


async def _send(provider: str, payload: dict) -> dict:
    return await cli_socket.request(socket_path(provider), payload, timeout=CONTROL_TIMEOUT, label=label(provider))


def _check(reply, handle_or_packet) -> dict:
    packet = handle_or_packet.packet if isinstance(handle_or_packet, Handle) else handle_or_packet
    try:
        return contract.validate_reply(reply, packet)
    except ValueError:
        raise RuntimeError(f"Invalid response from {label(packet.get('provider'))} bridge") from None


async def run(provider: str, fields: dict, *, auth_mode: str, on_progress=None) -> dict:
    """送出一回合並等到結束；回傳橋接的結果 dict（與舊同步回覆相同欄位），由各提供者的用戶端再驗。

    auth_mode 是該成員選的認證模式（FR-1），必須是轉接器登記過的模式。
    """
    track = TRACK.get()
    timeout = track.timeout if track is not None else contract.TIMEOUT_DEFAULT
    packet = contract.begin_packet(provider, str(uuid.uuid4()), fields, timeout, auth_mode=auth_mode)
    reply = await _send(provider, packet)
    epoch, turn = _check(reply, packet)
    handle = Handle(provider, packet, epoch, time.time(), stop_on_cancel=bool(track and track.stop_on_cancel))
    if track is not None:
        track.handle = handle
        if track.key:
            ACTIVE[track.key] = handle
    try:
        if track is not None and track.on_begin is not None:
            try:
                await asyncio.to_thread(track.on_begin, handle)
            except Exception:
                # 身分沒存下來就不能在 App 重啟後接回，也不能從畫面中斷；不讓它無人看管地跑下去。
                await asyncio.shield(_stop_quietly(handle))
                raise RuntimeError("回合身分未能保存，已要求橋接中斷這一回合") from None
        result = await observe(handle, turn, on_progress=on_progress)
        if track is not None:
            track.received = True
        return result
    except asyncio.CancelledError:
        if handle.stop_on_cancel:
            await asyncio.shield(_stop_quietly(handle))
        raise
    finally:
        if track is not None and track.key and ACTIVE.get(track.key) is handle:
            del ACTIVE[track.key]


async def observe(handle: Handle, turn: dict | None = None, *, on_progress=None) -> dict:
    loop = asyncio.get_running_loop()
    # 牆鐘上限以橋接接受時刻起算（接回時同樣適用），再加寬限讓橋接自己的逾時先回報。
    remaining = handle.timeout + DEADLINE_GRACE - max(0.0, time.time() - handle.started_at)
    deadline = loop.time() + remaining
    since, failures = 0, 0
    while True:
        if turn is not None:
            for entry in turn["progress"]:
                if entry["seq"] <= since:
                    continue
                since = entry["seq"]
                if on_progress is not None:
                    try:
                        on_progress(entry["item"])
                    except Exception:
                        pass
            state = turn["state"]
            if state == "done":
                if turn["result"] is None:
                    raise TurnUnknown("result_taken")
                return turn["result"]
            if state == "failed":
                raise RuntimeError(turn["error"] or f"{label(handle.provider)} bridge failed")
            if state == "stopped":
                raise TurnInterrupted(INTERRUPTED_TEXT)
            if state == "unknown":
                raise TurnUnknown(turn["error"])
        if loop.time() > deadline:
            raise TurnUnknown("deadline")
        await asyncio.sleep(POLL_SECONDS)
        try:
            reply = await _send(handle.provider, contract.control_packet(
                contract.ACTION_STATUS, handle.packet, handle.epoch, since))
            _, turn = _check(reply, handle)
            failures = 0
        except (RuntimeError, OSError, asyncio.TimeoutError):
            turn, failures = None, failures + 1
            if failures >= TRANSPORT_RETRIES:
                raise TurnUnknown("transport") from None


async def stop_handle(handle: Handle) -> str:
    """送 turn_stop；回傳橋接當下的狀態（stopping／stopped／unknown…）。"""
    reply = await _send(handle.provider, contract.control_packet(contract.ACTION_STOP, handle.packet, handle.epoch))
    return _check(reply, handle)[1]["state"]


async def _stop_quietly(handle: Handle) -> None:
    try:
        await stop_handle(handle)
    except Exception:
        logger.warning("Worker turn stop request failed")


async def stop(key: str) -> bool:
    """中斷正在觀察中的回合；觀察者會看到 stopped 並自行存檔。沒有觀察中的回合回 False。"""
    handle = ACTIVE.get(key)
    if handle is None:
        return False
    await stop_handle(handle)
    return True


async def ack(handle: Handle) -> None:
    try:
        await _send(handle.provider, contract.control_packet(contract.ACTION_ACK, handle.packet, handle.epoch))
    except Exception:
        # ack 只是讓橋接早點丟掉回覆全文；失敗時橋接會在容量滿時自行清掉已結束的紀錄。
        logger.warning("Worker turn ack failed")
