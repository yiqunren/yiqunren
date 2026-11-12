"""私聊 CLI 的有界取消清理；只操作已核對出生身分的自有程序群組。"""
from __future__ import annotations

import asyncio
import contextvars
import os
from pathlib import Path
import signal

from scripts.discussion_host import birth_receipt, group_ended
from scripts.host_diagnostics import TAIL_ATTRIBUTE, TAIL_LIMIT

TERMINATE_GRACE = 5
OUTPUT_LIMIT = 2_000_000
# 非同步回合（scripts/turn_host.py）在自己的 task 內設定這一回合的逾時秒數；
# communicate_private 以它取代橋接模組的 TIMEOUT_SECONDS。舊的同步私聊沒有設定，行為不變。
TURN_TIMEOUT: contextvars.ContextVar[int | None] = contextvars.ContextVar("yiqunren_turn_timeout", default=None)
STOP_UNCONFIRMED = '私聊 CLI 停止狀態未知'


class ProcessTally:
    """一回合內 communicate_private 被呼叫幾次、其中幾次確認了程序群組已結束（turn_host 的 guard 據此決定能否釋放）。

    用可變物件而不是直接 set ContextVar：Python 3.10 的 asyncio.wait_for 在複製的 context 裡跑，
    在那裡 set 的值傳不回呼叫端；同一物件的計數則雙方都看得到。
    """
    __slots__ = ("started", "confirmed")

    def __init__(self):
        self.started = 0
        self.confirmed = 0

    def all_confirmed(self) -> bool:
        return self.started > 0 and self.confirmed == self.started


TURN_PROCESSES: contextvars.ContextVar[ProcessTally | None] = contextvars.ContextVar(
    "yiqunren_turn_processes", default=None)


def _tail_buffer(process, name):
    """stdout／stderr 各自最後 64 KiB，記在 process 上供失敗診斷（逾時時回傳值會遺失，這裡仍在）。"""
    tails = getattr(process, TAIL_ATTRIBUTE, None)
    if not isinstance(tails, dict):
        tails = {}
        try:
            setattr(process, TAIL_ATTRIBUTE, tails)
        except AttributeError:
            return None
    return tails.setdefault(name, bytearray())


async def _communicate_bounded(process, message, tasks, on_stdout_line=None):
    exceeded = asyncio.Event()

    async def read(stream, keep, on_line=None, name=None):
        output, size, pending = bytearray(), 0, bytearray()
        tail = _tail_buffer(process, name) if name else None
        while chunk := await stream.read(8192):
            size += len(chunk)
            if tail is not None:
                tail.extend(chunk)
                if len(tail) > TAIL_LIMIT:
                    del tail[:len(tail) - TAIL_LIMIT]
            if size > OUTPUT_LIMIT:
                exceeded.set()
            elif keep:
                output.extend(chunk)
                if on_line is not None:
                    # 邊讀邊把完整的行交給呼叫端（進度回報）；回呼失敗不影響讀取與回覆。
                    pending.extend(chunk)
                    while (index := pending.find(b'\n')) != -1:
                        line = bytes(pending[:index])
                        del pending[:index + 1]
                        try:
                            on_line(line)
                        except Exception:
                            pass
            # 超限後繼續丟棄輸出，讓停止程序時的 pipe 能正常關閉。
        return bytes(output)

    async def feed():
        try:
            process.stdin.write(message)
            await process.stdin.drain()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            process.stdin.close()

    tasks.extend(asyncio.create_task(operation) for operation in (
        read(process.stdout, True, on_stdout_line, "stdout"), read(process.stderr, False, name="stderr"),
        feed(), process.wait()))
    completion = asyncio.gather(*tasks)
    limit = asyncio.create_task(exceeded.wait())
    tasks.extend((completion, limit))
    await asyncio.wait((completion, limit), return_when=asyncio.FIRST_COMPLETED)
    if exceeded.is_set():
        raise RuntimeError('私聊 CLI 輸出超過 2 MB 限制')
    stdout, _, _, _ = await completion
    return stdout, b''


async def _finish_io(tasks):
    for task in tasks:
        if not task.done():
            task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


def _signal_process(process, receipt, selected_signal):
    try:
        if receipt is not None:
            # 領頭程序的 PID、出生時間、session、UID 與 boot 都必須仍相符。
            if birth_receipt(process.pid) == receipt:
                os.killpg(receipt['pgid'], selected_signal)
        elif process.returncode is None:
            # 出生收據取得前已失敗時，只能清理 asyncio 持有的直接子程序。
            (process.terminate if selected_signal == signal.SIGTERM else process.kill)()
    except (FileNotFoundError, ProcessLookupError):
        pass


def _ended(process, receipt):
    if process.returncode is None:
        return False
    if receipt is not None:
        return group_ended(receipt)
    # 快速退出的 CLI 可能早於收據讀取；只查群組是否消失，不以猜測身分發訊號。
    try:
        os.killpg(process.pid, 0)
    except ProcessLookupError:
        return True
    return False


async def _wait_ended(process, receipt):
    await process.wait()
    while not _ended(process, receipt):
        await asyncio.sleep(.01)


async def _stop_process(process: asyncio.subprocess.Process, receipt) -> None:
    _signal_process(process, receipt, signal.SIGTERM)
    try:
        await asyncio.wait_for(_wait_ended(process, receipt), TERMINATE_GRACE)
    except asyncio.TimeoutError:
        _signal_process(process, receipt, signal.SIGKILL)
        try:
            await asyncio.wait_for(_wait_ended(process, receipt), TERMINATE_GRACE)
        except asyncio.TimeoutError:
            raise RuntimeError(STOP_UNCONFIRMED) from None


async def communicate_private(process, message: bytes, timeout: float, *, on_stdout_line=None):
    """等待回應；取消或其他中斷先清理，再傳遞原本的例外。

    on_stdout_line（可省略）：每收到一行完整 stdout 就以 bytes 呼叫，用於進度回報；
    不改變回傳值、逾時、輸出上限或清理行為。
    非同步回合設了 TURN_PROCESSES 時，記一次呼叫；正常返回前群組已結束、或例外清理確認群組消失，再記一次確認。
    """
    receipt = None
    tasks = []
    override = TURN_TIMEOUT.get()
    if override is not None:
        timeout = override
    tally = TURN_PROCESSES.get()
    if tally is not None:
        tally.started += 1
    confirmed = False
    try:
        try:
            receipt = birth_receipt(process.pid)
        except (FileNotFoundError, ProcessLookupError):
            pass
        # 只在有回呼時才多傳一個參數，既有以三參數替身取代 _communicate_bounded 的測試不受影響。
        bounded = (_communicate_bounded(process, message, tasks) if on_stdout_line is None
                   else _communicate_bounded(process, message, tasks, on_stdout_line))
        result = await asyncio.wait_for(bounded, timeout)
        if not _ended(process, receipt):
            raise RuntimeError('私聊 CLI 程序群組尚未結束')
        confirmed = True
        await _finish_io(tasks)
        return result
    except BaseException:
        async def stop_and_finish():
            try:
                await _stop_process(process, receipt)
            finally:
                await _finish_io(tasks)
        cleanup = asyncio.create_task(stop_and_finish())
        # 重複取消不能切斷有時間上限的清理；不建立脫離呼叫的背景工作。
        while not cleanup.done():
            try:
                await asyncio.shield(cleanup)
            except asyncio.CancelledError:
                continue
        cleanup.result()
        # 走到這裡代表 _stop_process 確認群組已消失；確認不了時上一行已丟 STOP_UNCONFIRMED。
        confirmed = True
        raise
    finally:
        if confirmed and tally is not None:
            tally.confirmed += 1
