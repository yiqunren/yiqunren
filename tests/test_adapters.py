"""SPEC NFR-7 › MVP 轉接器登記處：登記資料驗證，以及新增／移除轉接器後各行為都跟著登記處走。

全部離線：不連 socket、不啟動 CLI。
"""
from __future__ import annotations

import asyncio
import dataclasses
import json
import time
from types import MappingProxyType, SimpleNamespace
from uuid import uuid4

import pytest

from app.services import adapters, dispatcher_guidance, turn_contract, worker_turn
from app.services import discussion_contract as dc
from app.services.consultants.profiles import PROFILES
from app.services.dispatch_context import validate_context
from scripts import host_diagnostics, turn_host

TEST_FIELDS = frozenset({"message", "session_id"})


def make_adapter(code="testbot", **changes):
    base = dict(code=code, name="Test Bot", turn_fields=TEST_FIELDS, auth_modes=("api_key",),
                strengths=("測試用能力",), weaknesses=("測試用弱點",), choose_when="測試用。")
    return adapters.Adapter(**{**base, **changes})


def with_testbot(**changes):
    return adapters.override((*adapters.adapters(), make_adapter(**changes)))


def without(code):
    return adapters.override(tuple(entry for entry in adapters.adapters() if entry.code != code))


def snapshot(codes):
    unknown = {"status": "unknown", "remaining_percent": None, "resets_at": None}
    return {"v": 1, "as_of": "2026-11-12T00:00:00+00:00",
            "workers": {code: {"model": "", "effort": "", "configured": True, "weekly": dict(unknown)} for code in codes},
            "consultants": {"enabled": list(PROFILES), "disabled": [], "unknown": []}}


def discussion_run():
    return {"run_id": str(uuid4()), "conversation_id": "conv-test", "message": "議題",
            "context": [], "snapshots": {s: {"model": "model", "effort": "medium"} for s in dc.speakers()},
            "bridge_epochs": {code: str(uuid4()) for code in adapters.codes()},
            "state": "running", "version": 1, "stop_requested": False, "seal_confirmed": False,
            "calls": [], "events": []}


def run_whole_discussion(run):
    """依序產生每一格的封包並記成有效發言；回傳全部封包。"""
    packets = []
    for ordinal in range(1, dc.max_calls(run.get("participants")) + 1):
        packet = dc.make_packet(run, ordinal)
        dc.validate_begin(packet)
        packets.append(packet)
        run["calls"].append({"ordinal": ordinal, "call_id": packet["call_id"], "speaker": packet["speaker"],
                             "content": f"answer-{ordinal}", "execution": "ended", "result": "valid",
                             "admission": "accepted", "published": True, "receipt": {"pid": 100}})
    return packets


def begin(provider, fields=None, auth_mode="api_key"):
    return turn_contract.begin_packet(provider, str(uuid4()), fields or {key: "" for key in TEST_FIELDS}, 900,
                                      auth_mode=auth_mode)


def fake_process():
    process = SimpleNamespace(returncode=1)
    setattr(process, host_diagnostics.TAIL_ATTRIBUTE, {"stdout": bytearray(), "stderr": bytearray()})
    return process


def diag(provider, root):
    return host_diagnostics.record(provider, process=fake_process(), argv=["cli"], reason="timeout",
                                   started=time.monotonic(), root=root)


# ---- 預設登記 ----

def test_default_registry_follows_spec():
    assert adapters.codes() == ("codex", "grok", "claude_code")
    assert [entry.name for entry in adapters.adapters()] == ["Codex", "Grok", "Claude Code"]
    assert adapters.get("codex").auth_modes == ("api_key", "subscription_cli")
    assert adapters.get("grok").auth_modes == ("api_key", "subscription_cli")
    assert adapters.get("claude_code").auth_modes == ("api_key",)
    assert dc.host_candidates() == ("codex", "claude_code")
    assert {entry.code: entry.error_class_rule for entry in adapters.adapters()} == {
        "codex": None, "grok": None, "claude_code": "claude_events"}


def test_api_key_mode_is_not_registered_as_a_separate_adapter():
    assert not adapters.is_registered("claude_code_api")
    with pytest.raises(ValueError):
        begin("claude_code_api", {"message": "", "session_id": "", "workspace": "", "model": "",
                                  "effort": "", "max_budget_usd": 1})


BASE = {"message": "", "session_id": "", "workspace": "", "model": "", "effort": ""}


def test_turn_fields_depend_on_auth_mode():
    assert adapters.get("claude_code").fields_for("api_key") == frozenset({*BASE, "max_budget_usd"})
    packet = begin("claude_code", {**BASE, "max_budget_usd": 1})
    assert packet["protocol"] == 2 and packet["auth_mode"] == "api_key"
    for provider, fields, mode in (
        ("claude_code", BASE, "api_key"),                              # 缺 API key 模式的專屬欄位
        ("claude_code", BASE, "subscription_cli"),                     # Claude Code 尚未開放訂閱 CLI 模式
        ("grok", {**BASE, "max_budget_usd": 1}, "subscription_cli"),   # 專屬欄位不能帶到別家
        ("grok", BASE, "oauth"), ("grok", BASE, None), ("grok", BASE, ""),
    ):
        with pytest.raises(ValueError):
            begin(provider, fields, mode)
    assert begin("grok", BASE, "subscription_cli")["auth_mode"] == "subscription_cli"


def test_auth_mode_is_required_and_fingerprinted():
    packet = begin("grok", BASE, "subscription_cli")
    switched = {**packet, "auth_mode": "api_key"}
    with pytest.raises(ValueError, match="指紋"):
        turn_contract.validate_begin(switched, "grok")
    missing = {k: v for k, v in packet.items() if k != "auth_mode"}
    missing["call_hash"] = turn_contract.call_hash(missing)
    with pytest.raises(ValueError):
        turn_contract.validate_begin(missing, "grok")
    old = {**missing, "protocol": 1}
    old["call_hash"] = turn_contract.call_hash(old)
    with pytest.raises(ValueError):
        turn_contract.validate_begin(old, "grok")


def test_turn_host_hands_auth_mode_to_bridge_validate():
    seen = []

    def validate(fields, auth_mode):
        seen.append(auth_mode)
        return fields

    async def run(fields, progress, guard):
        return {"content": "ok"}

    async def scenario():
        host = turn_host.TurnHost("grok", validate=validate, run=run)
        packet = begin("grok", BASE, "subscription_cli")
        await host.handle(packet)
        await host.calls[packet["request_id"]]["task"]
        return host.calls[packet["request_id"]]["state"]

    assert asyncio.run(scenario()) == "done"
    assert seen == ["subscription_cli"]


def test_mode_fields_must_belong_to_a_registered_mode_and_not_overlap():
    for mode_fields in ({"subscription_cli": frozenset({"extra"})}, {"api_key": frozenset({"message"})},
                        {"api_key": frozenset()}, {"api_key": {"extra"}}, [("api_key", frozenset({"extra"}))]):
        with pytest.raises(ValueError):
            make_adapter(mode_fields=mode_fields)


def test_registration_data_cannot_be_mutated():
    entry = adapters.get("claude_code")
    with pytest.raises(dataclasses.FrozenInstanceError):
        entry.name = "Other"
    assert isinstance(entry.turn_fields, frozenset)
    assert isinstance(entry.mode_fields, MappingProxyType)
    with pytest.raises(TypeError):
        entry.mode_fields["subscription_cli"] = frozenset({"x"})
    assert all(isinstance(value, frozenset) for value in entry.mode_fields.values())
    assert all(type(getattr(entry, name)) is tuple for name in ("auth_modes", "strengths", "weaknesses", "model_tiers"))
    # 呼叫端拿到的副本改了也不影響登記處。
    source = {"api_key": frozenset({"extra"})}
    bot = make_adapter(mode_fields=source)
    source["api_key"] = frozenset({"changed"})
    assert bot.mode_fields["api_key"] == frozenset({"extra"})
    catalog = dispatcher_guidance.worker_capabilities()
    catalog["claude_code"]["strengths"].append("竄改")
    catalog["claude_code"]["name"] = "竄改"
    assert dispatcher_guidance.worker_capabilities()["claude_code"]["name"] == "Claude Code"
    assert "竄改" not in adapters.get("claude_code").strengths
    assert hash(entry) == hash(adapters.get("claude_code"))


def test_error_class_rule_names_match_host_diagnostics():
    assert set(host_diagnostics.ERROR_CLASS_RULES) == set(adapters.ERROR_CLASS_RULES)


# ---- 登記資料驗證 ----

@pytest.mark.parametrize("code", ["Codex", "co-dex", "1bot", "", "a" * 33, "bot!", "_bot", None])
def test_code_allows_only_lowercase_letters_digits_and_underscore(code):
    with pytest.raises(ValueError):
        make_adapter(code=code)


@pytest.mark.parametrize("change", [
    {"name": ""}, {"name": "a\nb"}, {"turn_fields": frozenset()}, {"turn_fields": {"message"}},
    {"turn_fields": frozenset({"Message"})}, {"auth_modes": ()}, {"auth_modes": ("oauth",)},
    {"auth_modes": ("api_key", "api_key")}, {"auth_modes": ["api_key"]}, {"strengths": ()},
    {"choose_when": " "}, {"model_tiers": ("a", "b")}, {"model_tiers": ("a", "b", "")},
    {"tier_note": "只有備註"}, {"host_output": "free_text"}, {"error_class_rule": "made_up"},
    {"socket_name": "../escape.sock"}, {"socket_name": "/abs/path.sock"}, {"socket_name": "bot"},
])
def test_invalid_registration_is_rejected(change):
    with pytest.raises(ValueError):
        make_adapter(**change)


def test_override_rejects_duplicates_or_empty_and_always_restores():
    before = adapters.adapters()
    for entries in ((), (make_adapter(), make_adapter()), ("codex",)):
        with pytest.raises(ValueError):
            with adapters.override(entries):
                pass
    with pytest.raises(RuntimeError):
        with adapters.override((make_adapter(),)):
            raise RuntimeError("boom")
    assert adapters.adapters() == before


# ---- 連線位置 ----

def test_socket_path_uses_env_override_then_runtime_dir(monkeypatch):
    monkeypatch.delenv("YIQUNREN_CLAUDE_CODE_SOCKET", raising=False)
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/run/user/4242")
    assert adapters.socket_env("claude_code") == "YIQUNREN_CLAUDE_CODE_SOCKET"
    assert worker_turn.socket_path("claude_code") == "/run/user/4242/yiqunren/claude_code.sock"
    monkeypatch.setenv("YIQUNREN_CLAUDE_CODE_SOCKET", "/srv/sockets/claude.sock")
    assert worker_turn.socket_path("claude_code") == "/srv/sockets/claude.sock"
    monkeypatch.setenv("YIQUNREN_CLAUDE_CODE_SOCKET", "relative/claude.sock")
    with pytest.raises(ValueError):
        worker_turn.socket_path("claude_code")


def test_socket_path_without_runtime_dir_falls_back_under_home(monkeypatch, tmp_path):
    monkeypatch.delenv("YIQUNREN_CODEX_SOCKET", raising=False)
    monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert worker_turn.socket_path("codex") == str(tmp_path / ".local/state/yiqunren/run/codex.sock")


def test_registered_socket_name_is_used(monkeypatch):
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/run/user/4242")
    monkeypatch.delenv("YIQUNREN_TESTBOT_SOCKET", raising=False)
    with with_testbot(socket_name="bot-bridge.sock"):
        assert worker_turn.socket_path("testbot") == "/run/user/4242/yiqunren/bot-bridge.sock"


# ---- 驗收：登記一個測試用的轉接器之後，各行為都看得到它 ----

def test_registered_adapter_is_accepted_by_turn_protocol():
    with with_testbot():
        packet = begin("testbot")
        assert turn_contract.validate_begin(packet, "testbot") is packet
        with pytest.raises(ValueError):
            begin("testbot", {"message": "", "thread_id": ""})
        handle = worker_turn.Handle.from_record({"provider": "testbot", "request_id": str(uuid4()),
                                                 "call_hash": "0" * 64, "epoch": str(uuid4()),
                                                 "timeout": 900, "started_at": 0})
        assert handle.provider == "testbot" and worker_turn.label("testbot") == "Test Bot"
        assert turn_host.TurnHost("testbot", validate=dict, run=None).provider == "testbot"


def test_registered_adapter_appears_in_dispatch_snapshot_and_prompt():
    with with_testbot():
        codes = adapters.codes()
        assert codes[-1] == "testbot"
        validate_context(snapshot(codes))
        with pytest.raises(ValueError):
            validate_context(snapshot(codes[:-1]))
        prompt = dispatcher_guidance.build_route_prompt("hi", [], context=snapshot(codes))
        assert "可執行工作者僅有 codex、grok、claude_code、testbot；" in prompt
        assert '"testbot":{"name":"Test Bot","strengths":["測試用能力"]' in prompt


def test_registered_adapter_joins_discussion_order():
    with with_testbot():
        members = ("codex", "grok", "claude_code", "testbot")
        assert dc.order() == ("dispatcher", *members, "dispatcher", *members, "dispatcher")
        assert dc.max_calls() == 11
        run = discussion_run()
        packets = run_whole_discussion(run)
        assert [p["speaker"] for p in packets] == list(dc.order())
        identity = json.loads(packets[4]["prompt"].rsplit("\n", 1)[1])["identity"]
        assert identity == {"speaker": "testbot", "name": "Test Bot", "role": "討論參與者", "member_number": 5,
                            "configured_model": "model", "configured_effort": "medium", "speech_ordinal": 5}
        # 首輪看不到同輪他人；次輪看得到首輪與追問（第 1～6 格）；結論格看得到前面全部。
        assert "answer-2" not in packets[4]["prompt"]
        assert all(f"answer-{n}" in packets[9]["prompt"] for n in range(1, 7))
        assert "answer-7" not in packets[9]["prompt"]
        assert dc.host_schema(6)["properties"]["decision"]["enum"] == ["continue", "finish"]
        assert dc.host_schema(11)["properties"]["decision"]["enum"] == ["finish"]
        with pytest.raises(ValueError):
            dc.host_schema(5)
        assert dc.public_run(run)["request_limit"] == 11
        failed = {"speaker": "testbot", "admission": "accepted", "execution": "ended",
                  "result": "error", "receipt": {"pid": 100}}
        assert dc.failed_member(failed)


def test_registered_adapter_gets_diagnostics_without_error_class(tmp_path):
    with with_testbot():
        assert diag("testbot", tmp_path)
        body = next((tmp_path / "testbot").glob("*.log")).read_text(encoding="utf-8")
        assert "provider: testbot" in body and "error_class" not in body


# ---- 驗收：移除一個轉接器之後，各行為都看不到它 ----

def test_removed_adapter_is_gone_from_turn_protocol():
    fields = {"message": "", "session_id": "", "workspace": "", "model": "", "effort": ""}
    packet = begin("grok", fields)
    with without("grok"):
        with pytest.raises(ValueError):
            begin("grok", fields)
        with pytest.raises(ValueError):
            turn_contract.validate_begin(packet, "grok")
        with pytest.raises(ValueError):
            worker_turn.socket_path("grok")
        with pytest.raises(ValueError):
            turn_host.TurnHost("grok", validate=dict, run=None)


def test_removed_adapter_is_gone_from_dispatch_snapshot_and_prompt():
    with without("grok"):
        validate_context(snapshot(("codex", "claude_code")))
        with pytest.raises(ValueError):
            validate_context(snapshot(("codex", "grok", "claude_code")))
        prompt = dispatcher_guidance.build_route_prompt("hi", [], context=snapshot(("codex", "claude_code")))
        assert "可執行工作者僅有 codex、claude_code；" in prompt
        assert "grok" not in prompt.lower()


def test_removed_adapter_is_gone_from_discussion():
    with without("grok"):
        assert dc.order() == ("dispatcher", "codex", "claude_code", "dispatcher", "codex", "claude_code", "dispatcher")
        run = discussion_run()
        packets = run_whole_discussion(run)
        rosters = [[m["speaker"] for m in json.loads(p["prompt"].rsplit("\n", 1)[1])["participants"]] for p in packets]
        assert all(roster == ["dispatcher", "codex", "claude_code"] for roster in rosters)
        assert all("grok" not in p["prompt"].lower() for p in packets)
        assert all(p["speaker"] != "grok" for p in packets)
        assert dc.public_run(run)["request_limit"] == 7
        assert not dc.failed_member({"speaker": "grok", "admission": "accepted", "execution": "ended",
                                     "result": "error", "receipt": {"pid": 100}})


def test_removed_adapter_gets_no_diagnostics(tmp_path):
    with without("grok"):
        assert diag("grok", tmp_path) is None
    assert not (tmp_path / "grok").exists()


def test_removing_the_default_host_moves_hosting_to_the_next_candidate():
    with without("codex"):
        assert dc.host_order() == ["claude_code"]
        run = discussion_run()
        packet = dc.make_packet(run, 1)
        assert "host_provider" not in packet and packet["epoch"] == run["bridge_epochs"]["claude_code"]
        assert dc.PROMPT_HOST_FORMAT in packet["prompt"]


# ---- 驗收：未登記的代號一律拒絕 ----

def test_unregistered_code_is_rejected_everywhere(tmp_path):
    with pytest.raises(ValueError):
        adapters.get("nobody")
    with pytest.raises(ValueError):
        begin("nobody")
    with pytest.raises(ValueError):
        worker_turn.Handle.from_record({"provider": "nobody", "request_id": str(uuid4()), "call_hash": "0" * 64,
                                        "epoch": str(uuid4()), "timeout": 900, "started_at": 0})
    with pytest.raises(ValueError):
        worker_turn.socket_path("nobody")
    assert worker_turn.label("nobody") == "worker"
    with pytest.raises(ValueError):
        turn_host.TurnHost("nobody", validate=dict, run=None)
    with pytest.raises(ValueError):
        validate_context(snapshot((*adapters.codes(), "nobody")))
    assert diag("nobody", tmp_path) is None and not (tmp_path / "nobody").exists()
    run = discussion_run()
    run["host_provider"] = "nobody"
    with pytest.raises(ValueError):
        dc.make_packet(run, 1)
    with pytest.raises(ValueError):
        dc.speaker_name(discussion_run(), "nobody")


# ---- FR-3 參與名單：發言者與順序以本場參與名單計算 ----

def test_two_participants_give_seven_slots():
    run = discussion_run()
    run["participants"] = ["grok", "codex"]
    assert dc.members(run["participants"]) == ("codex", "grok")  # 依登記順序，不依名單順序
    assert dc.order(run["participants"]) == ("dispatcher", "codex", "grok", "dispatcher", "codex", "grok", "dispatcher")
    assert dc.max_calls(run["participants"]) == 7
    packets = run_whole_discussion(run)
    assert len(packets) == 7 and all(p["participants"] == ["codex", "grok"] for p in packets)
    roster = json.loads(packets[1]["prompt"].rsplit("\n", 1)[1])["participants"]
    assert [(m["speaker"], m["member_number"]) for m in roster] == [("dispatcher", 1), ("codex", 2), ("grok", 3)]
    assert dc.public_run(run)["request_limit"] == 7
    assert dc.host_schema(4, participants=run["participants"])["properties"]["decision"]["enum"] == ["continue", "finish"]
    assert dc.host_result('{"decision":"finish","content":"結論"}', 7, participants=run["participants"])
    with pytest.raises(ValueError):
        dc.host_schema(5, participants=run["participants"])


def test_participants_default_to_all_registered():
    assert dc.order() == dc.order(list(adapters.codes()))
    assert "participants" not in dc.make_packet(discussion_run(), 1)


@pytest.mark.parametrize("participants", [
    ["codex"], [], ["codex", "nobody"], ["codex", "codex"], ["codex", "claude_code_api"], "codex,grok", [None, "codex"],
])
def test_participant_list_rejects_unregistered_or_fewer_than_two(participants):
    with pytest.raises(ValueError):
        dc.order(participants)
    run = discussion_run()
    run["participants"] = participants
    with pytest.raises(ValueError):
        dc.make_packet(run, 1)


def test_packet_participants_must_be_canonical_and_fingerprinted():
    run = discussion_run()
    run["participants"] = ["codex", "grok"]
    packet = dc.make_packet(run, 2)
    unpinned = {k: v for k, v in packet.items() if k != "participants"}
    assert dc.call_fingerprint(unpinned) != packet["call_hash"]
    for change in (["grok", "codex"], ["codex", "nobody"], ["codex"], ("codex", "grok")):
        bad = {**packet, "participants": change}
        bad["call_hash"] = dc.call_fingerprint(bad)
        with pytest.raises(ValueError):
            dc.validate_begin(bad)
    # 名單外的轉接器不能出現在這場的格位上。
    outsider = {**packet, "speaker": "claude_code"}
    outsider["call_hash"] = dc.call_fingerprint(outsider)
    with pytest.raises(ValueError):
        dc.validate_begin(outsider)


# ---- 主持人候選與順序 ----

def test_host_order_follows_owner_list_and_enabled_adapters():
    assert dc.host_order(["claude_code"]) == ["claude_code"]
    assert dc.host_order(["claude_code", "codex"]) == ["claude_code", "codex"]
    assert dc.host_order([]) == ["codex", "claude_code"]
    assert dc.host_order(None, enabled=["claude_code", "grok"]) == ["claude_code"]
    assert dc.host_order("codex", enabled=["grok"]) == []
    for bad in (["codex", "codex"], ["codex", "nobody"], ["grok"], [1], {"codex"}):
        with pytest.raises(ValueError):
            dc.host_order(bad)
    with pytest.raises(ValueError):
        dc.host_order(None, enabled=["nobody"])


def test_host_order_default_follows_registration_order():
    reordered = (adapters.get("claude_code"), adapters.get("codex"), adapters.get("grok"))
    with adapters.override(reordered):
        assert dc.host_order() == ["claude_code", "codex"]
        assert dc.alternate_hosts() == ("codex",)


# ---- 模型等級 ----

def test_model_names_appear_only_for_registered_tiers():
    tiers = ("Alpha Low", "Beta Mid", "Gamma High")
    with with_testbot(model_tiers=tiers, tier_note="Alpha 只搭配 Low"):
        assert "Test Bot 配置對應 Alpha Low／Beta Mid／Gamma High，Alpha 只搭配 Low" in dispatcher_guidance.build_route_prompt("hi", [])
    codex = dataclasses.replace(adapters.get("codex"), model_tiers=None, tier_note="")
    with adapters.override((codex, adapters.get("grok"), adapters.get("claude_code"))):
        prompt = dispatcher_guidance.build_route_prompt("hi", [])
        assert "Codex 沿用使用者已設定的模型與推理強度" in prompt
        assert not any(name in prompt for name in ("Luna", "Sol Medium", "Astra"))
        assert "Sonnet Low／Sonnet Medium／Opus High" in prompt
