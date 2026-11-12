"""三家私聊橋接共用的非同步工作者回合：接受後立即回覆，CLI 在橋接程序內繼續跑。

- turn_begin：驗欄位後建立 asyncio task 執行既有的 _run_codex／_run_claude／_run_request，立即回 running。
- turn_status：回目前狀態、新的進度項與（完成時）回覆；查詢不延長逾時。
- turn_stop：取消該 task；private_cli.communicate_private 會對已核對出生身分的程序群組送 SIGTERM，
  5 秒後 SIGKILL，確認群組消失才結束。確認不了時狀態為 unknown。
- turn_ack：App 存檔後丟掉回覆全文。

寫入權：沿用 data/write-ownership 登記。執行期間每分鐘續期；成功、使用者中斷且程序群組已確認結束、
或橋接以 EndedBeforeWork 回報還沒開始工作時釋放；
其他失敗（逾時、非 0 退出、解析失敗等）若本回合每個 CLI 程序群組都確認結束、且工作區指紋與啟動前相同
（scripts/workspace_fingerprint.py）也釋放；其餘（停止未確認、橋接關閉、指紋取不到、工作區有變動）標 unknown，需人工核對。
每次處置在 stderr 記一行 `turn_host lease {...}`（原因與有變動的路徑）。
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import uuid

from app.services import adapters
from app.services import turn_contract as contract
from app.services.write_ownership import configured_registry
from scripts import private_cli, workspace_fingerprint

class EndedBeforeWork(RuntimeError):
    """CLI 程序群組已確認結束，而且橋接能證明這一回合沒有開始工作，寫入權可以直接釋放。

    Grok 的判斷是沒有輸出任何事件；Claude 見 claude_host_bridge._no_work_done。
    """


MAX_CALLS = 200
MAX_PROGRESS_KEPT = 500
LEASE_TTL = 300
RENEW_SECONDS = 60
SHUTDOWN_GRACE = 15


def max_timeout(name: str) -> int:
    """橋接可接受的單回合上限：環境變數（60～3600 的整數）優先，否則 3600；格式不對就拒絕啟動。"""
    value = os.environ.get(name)
    if not value:
        return contract.TIMEOUT_MAX
    try:
        seconds = int(value)
    except ValueError:
        raise ValueError(f"{name} 必須是整數秒數") from None
    if not contract.TIMEOUT_MIN <= seconds <= contract.TIMEOUT_MAX:
        raise ValueError(f"{name} 必須在 {contract.TIMEOUT_MIN}～{contract.TIMEOUT_MAX} 秒之間")
    return seconds


async def _settled(function, *args):
    """在執行緒跑登記庫操作；被取消時仍等交易落定，讓呼叫端知道結果（同 project_build.persist）。"""
    task = asyncio.ensure_future(asyncio.to_thread(function, *args))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        await task
        raise


class TurnHost:
    """validate(fields, auth_mode) 回傳已驗證的 fields（或拋 ValueError）；run(fields, progress, guard) 執行一回合並回傳結果 dict。
    auth_mode 已由 turn_contract 核對為該轉接器登記過的認證模式；橋接要用它時，自行放進 validate 的回傳值交給 run。

    guard(project, holder, operation, ttl) 與 write_ownership.guarded_write 同形狀，由各橋接在想要的時點呼叫
    （Grok 在 Kilo 鎖內、模型目錄核對之後才申請，與同步路徑相同）。
    """

    def __init__(self, provider, *, validate, run, maximum=contract.TIMEOUT_MAX, invalid="Invalid request",
                 failed="Bridge failed", clock=time.monotonic):
        if not adapters.is_registered(provider):
            raise ValueError("未知的回合提供者")
        self.provider, self.validate, self.run = provider, validate, run
        self.maximum, self.invalid, self.failed, self.clock = maximum, invalid, failed, clock
        self.epoch = str(uuid.uuid4())
        self.calls: dict[str, dict] = {}
        self.lock = asyncio.Lock()
        self.closing = False

    # ---- 協定 ----

    async def handle(self, packet) -> dict:
        action = packet.get("action") if isinstance(packet, dict) else None
        if action == contract.ACTION_BEGIN:
            contract.validate_begin(packet, self.provider, self.maximum)
            async with self.lock:
                return self._begin(packet)
        contract.validate_control(packet)
        call = self.calls.get(packet["request_id"]) if packet["epoch"] == self.epoch else None
        if call is None:
            # 不同 epoch 或沒有這筆：橋接曾重啟，原回合結果無法取得；不能證明程序已結束。
            return self._reply_missing(packet)
        if call["call_hash"] != packet["call_hash"]:
            raise ValueError("原請求指紋不符")
        if action == contract.ACTION_STOP:
            self._stop(call)
        elif action == contract.ACTION_ACK and call["state"] in contract.TERMINAL:
            call["result"], call["acked"] = None, True
        return self._reply(call, packet.get("since", 0))

    def _begin(self, packet) -> dict:
        if self.closing:
            raise RuntimeError("橋接正在關閉，未啟動")
        key = packet["request_id"]
        existing = self.calls.get(key)
        if existing is not None:
            if existing["call_hash"] != packet["call_hash"]:
                raise ValueError("同一回合識別的內容不同")
            return self._reply(existing, 0)
        fields = self.validate(dict(packet["fields"]), packet["auth_mode"])
        self._prune()
        call = {"request_id": key, "call_hash": packet["call_hash"], "timeout": packet["timeout"],
                "state": "running", "error": None, "result": None, "acked": False, "stop_requested": False,
                "started": self.clock(), "ended": None, "progress": [], "progress_seq": 0, "task": None}
        self.calls[key] = call
        call["task"] = asyncio.create_task(self._execute(call, fields))
        return self._reply(call, 0)

    def _prune(self):
        if len(self.calls) < MAX_CALLS:
            return
        # 先丟已 ack 的，再丟其他已結束的；執行中的永不丟。
        for acked_first in (True, False):
            for key in [k for k, c in self.calls.items()
                        if c["state"] in contract.TERMINAL and (c["acked"] or not acked_first)]:
                if len(self.calls) < MAX_CALLS:
                    return
                del self.calls[key]
        if len(self.calls) >= MAX_CALLS:
            raise RuntimeError("回合紀錄容量已滿，請等目前回合結束")

    def _stop(self, call):
        if call["state"] == "running":
            call.update(state="stopping", stop_requested=True)
            call["task"].cancel()

    def _elapsed(self, call) -> int:
        end = call["ended"] if call["ended"] is not None else self.clock()
        return max(0, int(end - call["started"]))

    def _reply(self, call, since) -> dict:
        # 完成時只帶回覆、不帶進度：回覆可到 100 KB，與進度合在一行會更接近 App 端 120 KB 的單行上限。
        items = ([] if call["state"] == "done" else
                 [entry for entry in call["progress"] if entry["seq"] > since][:contract.MAX_PROGRESS_BATCH])
        return {"ok": True, "epoch": self.epoch, "turn": {
            "request_id": call["request_id"], "call_hash": call["call_hash"], "state": call["state"],
            "error": call["error"], "elapsed": self._elapsed(call), "progress_seq": call["progress_seq"],
            "progress": [dict(entry) for entry in items],
            "result": call["result"] if call["state"] == "done" else None}}

    def _reply_missing(self, packet) -> dict:
        return {"ok": True, "epoch": self.epoch, "turn": {
            "request_id": packet["request_id"], "call_hash": packet["call_hash"], "state": "unknown",
            "error": "bridge_restarted", "elapsed": 0, "progress_seq": 0, "progress": [], "result": None}}

    # ---- 執行 ----

    def _collector(self, call):
        def collect(item):
            public = contract.public_progress(item)
            if public is None:
                return
            call["progress_seq"] += 1
            call["progress"].append({"seq": call["progress_seq"], "item": public})
            if len(call["progress"]) > MAX_PROGRESS_KEPT:
                del call["progress"][:-MAX_PROGRESS_KEPT]
        return collect

    def _guard(self, call):
        async def guard(project, holder, operation, _ttl=None):
            registry = configured_registry()
            claim = asyncio.ensure_future(asyncio.to_thread(registry.claim, str(project), ["."], holder, LEASE_TTL))
            try:
                lease = await asyncio.shield(claim)
            except asyncio.CancelledError:
                # 申請途中被中斷：等交易落定；若已登記，因為還沒啟動任何程序，直接釋放。
                try:
                    lease = await claim
                    await asyncio.to_thread(registry.change, lease["lease_id"], holder, "release")
                except Exception:
                    pass
                raise
            renew = asyncio.create_task(self._renew(registry, lease["lease_id"], holder))
            tally = private_cli.ProcessTally()
            token = private_cli.TURN_PROCESSES.set(tally)
            before = None
            try:
                # 在啟動 CLI 前取指紋；同步走訪，有上限（workspace_fingerprint），取消也不會留下半套狀態。
                before = workspace_fingerprint.take(project)
                result = await operation()
            except BaseException as exc:
                renew.cancel()
                await asyncio.gather(renew, return_exceptions=True)
                reason, changed, total = self._failure_reason(exc, call, project, before, tally)
                release = not reason.startswith("unknown")
                try:
                    await _settled(registry.change, lease["lease_id"], holder, "release" if release else "unknown")
                    state = "released" if release else "unknown"
                except Exception:
                    state = "change_failed"
                self._log_lease(holder, reason, state, changed, total)
                raise
            finally:
                private_cli.TURN_PROCESSES.reset(token)
            renew.cancel()
            await asyncio.gather(renew, return_exceptions=True)
            try:
                await _settled(registry.change, lease["lease_id"], holder, "release")
                state = "released"
            except Exception:
                # 登記已因逾期轉 unknown 等：回覆照常交出，登記維持 unknown 待人工核對。
                state = "change_failed"
            self._log_lease(holder, "completed", state)
            return result
        return guard

    @staticmethod
    def _failure_reason(exc, call, project, before, tally):
        """回合以例外結束時的寫入權處置：回傳（原因, 變動路徑, 變動總數）；原因以 unknown 開頭就不釋放。

        - 使用者中斷：communicate_private 確認程序群組結束後才會以 CancelledError 結束 → 釋放。
        - 橋接關閉（非使用者中斷的取消）→ unknown。
        - EndedBeforeWork：橋接能證明還沒開始工作 → 釋放。
        - 其他失敗（逾時、非 0 退出、解析失敗等）：本回合每個 CLI 程序群組都確認結束，
          而且工作區指紋與啟動前相同 → 釋放；否則 unknown（停止未確認、沒經過 communicate_private、
          指紋取不到或超過上限、工作區有變動）。
        """
        if isinstance(exc, asyncio.CancelledError):
            return ("interrupted" if call["stop_requested"] else "unknown:bridge_stopping"), [], 0
        if isinstance(exc, EndedBeforeWork):
            return "ended_before_work", [], 0
        if not tally.all_confirmed():
            return "unknown:unconfirmed", [], 0
        after = workspace_fingerprint.take(project) if before is not None else None
        if after is None:
            return "unknown:fingerprint_unavailable", [], 0
        changed, total = workspace_fingerprint.diff(before, after)
        if total:
            return "unknown:changed", changed, total
        return "unchanged_after_failure", [], 0

    def _log_lease(self, holder, reason, state, changed=(), total=0):
        """寫入權處置記到 stderr（systemd journal）；不寫診斷目錄，避免巡檢把它當成新失敗。只記路徑、不記內容。"""
        record = {"provider": self.provider, "holder": holder, "reason": reason, "state": state}
        if total:
            record.update(changed=list(changed), changed_total=total)
        try:
            print("turn_host lease " + json.dumps(record, ensure_ascii=False), file=sys.stderr, flush=True)
        except Exception:
            pass

    @staticmethod
    async def _renew(registry, lease_id, holder):
        while True:
            await asyncio.sleep(RENEW_SECONDS)
            try:
                await asyncio.to_thread(registry.change, lease_id, holder, "renew", LEASE_TTL)
            except Exception:
                # 續期失敗時登記會逾期轉 unknown；回合本身不因此中止。
                pass

    async def _execute(self, call, fields):
        private_cli.TURN_TIMEOUT.set(call["timeout"])
        try:
            result = await self.run(fields, self._collector(call), self._guard(call))
            if not isinstance(result, dict) or not isinstance(result.get("content"), str):
                raise RuntimeError(self.failed)
            call.update(state="done", result=result, error=None)
        except asyncio.CancelledError:
            if call["stop_requested"]:
                call.update(state="stopped", error="stopped")
            else:
                call.update(state="unknown", error="bridge_stopping")
        except RuntimeError as exc:
            message = str(exc)
            if message.startswith(private_cli.STOP_UNCONFIRMED):
                call.update(state="unknown", error="stop_unconfirmed")
            else:
                # 橋接的 RuntimeError 已是固定、可公開的說明（含診斷 ID），與同步路徑相同。
                call.update(state="failed", error=message[:contract.MAX_ERROR_CHARS])
        except ValueError:
            call.update(state="failed", error=self.invalid)
        except Exception:
            call.update(state="failed", error=self.failed)
        finally:
            call["ended"] = self.clock()

    async def shutdown(self):
        """橋接關閉：取消執行中的回合（程序會被回收），狀態記為 unknown，寫入權標 unknown。"""
        self.closing = True
        tasks = [c["task"] for c in self.calls.values() if c["task"] is not None and not c["task"].done()]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.wait(tasks, timeout=SHUTDOWN_GRACE)
