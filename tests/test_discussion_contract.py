"""群聊封包與盲首輪的純離線檢查。"""
import json
from copy import deepcopy
from uuid import uuid4

import pytest

from app.services import adapters
from app.services.discussion_contract import (MAX_WIRE, DiscussionCapacityError, DiscussionDiagnosticError, call_fingerprint, host_order, host_result,
                                             host_schema, make_packet, order, public_run, safe_diagnostic, settled_call, validate_begin, wire)


def sample_run():
    return {"run_id": str(uuid4()), "conversation_id": "conv-test", "message": "討論門口繞牆移動",
            "context": [{"source_id": "message:1", "speaker": "user", "content": "來源"}],
            "snapshots": {s: {"model": "xai/grok-4.7" if s == "grok" else "model", "effort": "medium"} for s in set(order())},
            "bridge_epochs": {p: str(uuid4()) for p in adapters.codes()},
            "state": "running", "version": 1, "stop_requested": False, "seal_confirmed": False,
            "calls": [], "events": []}


def add_result(run, ordinal):
    packet = make_packet(run, ordinal)
    run["calls"].append({"ordinal": ordinal, "call_id": packet["call_id"], "call_hash": packet["call_hash"],
        "speaker": order()[ordinal - 1], "content": f"answer-{ordinal}", "execution": "ended", "result": "valid",
        "admission": "accepted", "published": ordinal not in (2, 3, 4), "receipt": {"pid": 100}})


def prompt_data(packet):
    return json.loads(packet["prompt"].rsplit("\n", 1)[1])


@pytest.mark.parametrize("speaker", adapters.codes())
def test_ended_member_error_allows_next_slot_without_turning_into_success(speaker):
    call = {"speaker": speaker, "admission": "accepted", "execution": "ended",
            "result": "error", "receipt": {"pid": 100}}
    assert settled_call(call)
    assert call["result"] == "error"


@pytest.mark.parametrize("change", [
    {"speaker": "dispatcher"}, {"speaker": "unknown"}, {"admission": "unknown"},
    {"execution": "unknown"}, {"execution": "running"}, {"execution": "not_started"},
    {"result": "unknown"}, {"result": "pending"}, {"receipt": None},
    {"diagnostic": {"code": "tool_event_rejected"}}, {"diagnostic": {"code": "event_type_rejected"}},
    {"diagnostic": {"code": "item_type_rejected"}}, {"diagnostic": {"code": "event_shape_invalid"}},
    {"diagnostic": {"code": "event_json_invalid"}},
    {"diagnostic": {"code": "cli_error_event"}}, {"diagnostic": {"code": "cli_notice_event"}},
    {"diagnostic": {"code": "cancelled"}},
])
def test_uncertain_or_host_error_never_allows_next_slot(change):
    call = {"speaker": "codex", "admission": "accepted", "execution": "ended",
            "result": "error", "receipt": {"pid": 100}, **change}
    assert not settled_call(call)


@pytest.mark.parametrize("change", [{"admission": "unknown"}, {"admission": "not_accepted"}, {"receipt": None}])
def test_valid_label_does_not_override_missing_execution_evidence(change):
    call = {"speaker": "codex", "admission": "accepted", "execution": "ended",
            "result": "valid", "receipt": {"pid": 100}, **change}
    assert not settled_call(call)


@pytest.mark.parametrize("ordinal,speaker,number,name,role", [
    (1, "dispatcher", 1, "調度員", "主持人"),
    (2, "codex", 2, "Codex", "討論參與者"),
    (3, "grok", 3, "Grok", "討論參與者"),
    (4, "claude_code", 4, "Claude Code", "討論參與者"),
    (5, "dispatcher", 1, "調度員", "主持人"),
    (6, "codex", 2, "Codex", "討論參與者"),
    (7, "grok", 3, "Grok", "討論參與者"),
    (8, "claude_code", 4, "Claude Code", "討論參與者"),
    (9, "dispatcher", 1, "調度員", "主持人"),
])
def test_prompt_supplies_own_identity_roster_and_snapshot_model(ordinal, speaker, number, name, role):
    run = sample_run()
    run["snapshots"]["dispatcher"] = {"model": "host-model", "effort": "low"}
    run["snapshots"]["codex"] = {"model": "member-model", "effort": "high"}
    packet = make_packet(run, ordinal)
    data = prompt_data(packet)
    identity = data["identity"]
    assert identity == {"speaker": speaker, "name": name, "role": role, "member_number": number,
                        "configured_model": packet["model"], "configured_effort": packet["effort"],
                        "speech_ordinal": ordinal}
    assert [(p["speaker"], p["member_number"]) for p in data["participants"]] == [
        ("dispatcher", 1), ("codex", 2), ("grok", 3), ("claude_code", 4)]
    assert data["participants"][0]["configured_model"] == "host-model"
    assert data["participants"][1]["configured_model"] == "member-model"
    assert "實際執行模型未核實" in packet["prompt"]
    assert "不要使用工具、讀取檔案或執行任務" in packet["prompt"]
    validate_begin(packet)


def test_roll_call_keeps_numbers_after_skip_and_does_not_invent_default_model():
    run = sample_run()
    add_result(run, 1)
    run["calls"].append({"ordinal": 3, "speaker": "grok", "result": "skipped"})
    run["snapshots"]["claude_code"] = {"model": "", "effort": ""}
    packet = make_packet(run, 4)
    data = prompt_data(packet)
    assert data["identity"]["member_number"] == 4
    assert data["identity"]["configured_model"] == ""
    assert "空字串表示使用預設" in packet["prompt"]
    assert "跳過者保留編號" in packet["prompt"]
    assert "名冊不代表已發言或已成功" in packet["prompt"]
    host = prompt_data(make_packet(run, 5))
    assert host["skipped"] == [{"speaker": "grok", "reason": "weekly_quota_below_10_percent"}]


def test_first_round_has_identical_context_and_no_current_peer():
    run = sample_run()
    add_result(run, 1)
    packet2 = make_packet(run, 2)
    add_result(run, 2)
    packet3 = make_packet(run, 3)
    add_result(run, 3)
    packet4 = make_packet(run, 4)
    contexts = [prompt_data(p) for p in (packet2, packet3, packet4)]
    assert [c.pop("identity")["speaker"] for c in contexts] == ["codex", "grok", "claude_code"]
    assert contexts[0] == contexts[1] == contexts[2]
    assert "answer-1" in packet4["prompt"]
    assert "answer-2" not in packet4["prompt"]


def test_second_round_reads_full_first_round_and_same_review():
    run = sample_run()
    for n in range(1, 6):
        add_result(run, n)
    sixth = make_packet(run, 6)
    add_result(run, 6)
    seventh = make_packet(run, 7)
    contexts = [prompt_data(p) for p in (sixth, seventh)]
    assert [c.pop("identity")["speaker"] for c in contexts] == ["codex", "grok"]
    assert contexts[0] == contexts[1]
    assert all(f"answer-{n}" in sixth["prompt"] for n in range(1, 6))
    assert "answer-6" not in seventh["prompt"]


def test_wire_limit_applies_after_json_escape():
    with pytest.raises(DiscussionCapacityError, match="64 KiB"):
        wire({"prompt": '"' * (56 * 1024)})


@pytest.mark.parametrize("character,width", [("a", 1), ("原", 3), ("\\", 2), ("\x01", 6)])
def test_capacity_boundary_uses_encoded_bytes_without_changing_content(character, width):
    # 依 64 KiB 協定與 UTF-8／JSON 跳脫計算預期值，不讓待測 wire 決定測試邊界。
    limit = 64 * 1024
    assert MAX_WIRE == limit
    overhead = len(b'{"prompt":""}\n')
    count = (limit - overhead) // width
    payload = {"prompt": character * count}
    encoded = wire(payload)
    assert len(encoded) == overhead + count * width
    assert len(encoded) <= limit and limit - len(encoded) < width
    assert json.loads(encoded) == payload
    with pytest.raises(DiscussionCapacityError):
        wire({"prompt": character * (count + 1)})


@pytest.mark.parametrize("change", [
    {"call_id": "1"}, {"speaker": "grok"}, {"call_hash": "wrong"},
    {"cwd": "/home/user"}, {"model": "--danger"}, {"epoch": "bad"},
])
def test_bridge_packet_rejects_changed_identity_or_control_fields(change):
    packet = make_packet(sample_run(), 1)
    packet.update(change)
    if "call_hash" not in change:
        packet["call_hash"] = call_fingerprint(packet)
    with pytest.raises((ValueError, KeyError)):
        validate_begin(packet)


def test_decision_mode_is_the_only_extra_packet_field_and_is_fingerprinted():
    packet = make_packet(sample_run(), 1)
    plain_hash = packet["call_hash"]
    decided = {**packet, "mode": "decision"}
    decided["call_hash"] = call_fingerprint(decided)
    assert decided["call_hash"] != plain_hash
    validate_begin(decided)
    with pytest.raises(ValueError):
        validate_begin({**decided, "call_hash": plain_hash})
    for mode in ("vote", "discussion", None):
        bad = {**packet, "mode": mode}
        bad["call_hash"] = call_fingerprint(bad)
        with pytest.raises(ValueError):
            validate_begin(bad)


@pytest.mark.parametrize("ordinal", [1, 5, 9])
def test_host_schema_keeps_discussion_shape_and_strict_decision_objects(ordinal):
    decisions = {1: ["start", "needs_input"], 5: ["continue", "finish"], 9: ["finish"]}[ordinal]
    assert host_schema(ordinal) == {"type": "object", "properties": {"decision": {"type": "string", "enum": decisions},
                                    "content": {"type": "string"}}, "required": ["decision", "content"],
                                    "additionalProperties": False}
    def strict(node):
        if node.get("type") == "object":
            assert node["additionalProperties"] is False and set(node["required"]) == set(node["properties"])
            for child in node["properties"].values():
                strict(child)
        if node.get("type") == "array":
            strict(node["items"])
    strict(host_schema(ordinal, "decision"))
    with pytest.raises(ValueError):
        host_schema(ordinal, "vote")


@pytest.mark.parametrize("ordinal,decision", [(1, "start"), (1, "needs_input"), (5, "continue"), (5, "finish"), (9, "finish")])
def test_host_decisions_are_bounded(ordinal, decision):
    assert host_result(json.dumps({"decision": decision, "content": "文字"}), ordinal)["decision"] == decision


def test_host_cannot_add_rounds_or_extra_fields():
    for data in ({"decision": "continue", "content": "文字"},
                 {"decision": "finish", "content": "文字", "execute": True}):
        with pytest.raises(ValueError):
            host_result(json.dumps(data), 9)


HOST_REPLY = json.dumps({"decision": "start", "content": "開場文字"}, ensure_ascii=False)
OTHER_REPLY = json.dumps({"decision": "needs_input", "content": "另一份"}, ensure_ascii=False)
FOOTER = "\n\n小結：已完成開場；現在位於第 1 格；尚有無。\n下一步：① 建議繼續；③ NO－先修改方案。"


@pytest.mark.parametrize("reply", [
    f"  {HOST_REPLY}\n",
    f"```json\n{HOST_REPLY}\n```",
    f"```\n{HOST_REPLY}\n```",
    f"\n```JSON\n{HOST_REPLY}\n```\n",
    f"```json\n{HOST_REPLY}",
    HOST_REPLY + FOOTER,
    f"```json\n{HOST_REPLY}\n```{FOOTER}",
])
def test_host_reply_tolerates_code_fence_and_trailing_text(reply):
    assert host_result(reply, 1) == {"decision": "start", "content": "開場文字"}


@pytest.mark.parametrize("reply", [
    "好的，以下是結果：\n" + HOST_REPLY,
    "小結：沒有任何 JSON",
    "```json\n不是 JSON\n```",
    "```",
    "",
    f"{HOST_REPLY}\n{OTHER_REPLY}",
    f"{HOST_REPLY}{OTHER_REPLY}",
    f"{HOST_REPLY}\n\n修正版：\n{OTHER_REPLY}",
    f"```json\n{HOST_REPLY}\n```\n```json\n{OTHER_REPLY}\n```",
])
def test_host_reply_rejects_what_it_cannot_tell_apart(reply):
    with pytest.raises(ValueError):
        host_result(reply, 1)


@pytest.mark.parametrize("data", [{"decision": "continue", "content": "文字"},
                                  {"decision": "finish", "content": "文字", "execute": True}])
def test_tolerance_does_not_loosen_host_structure(data):
    with pytest.raises(ValueError):
        host_result(f"```json\n{json.dumps(data)}\n```{FOOTER}", 9)


def test_public_projection_hides_process_and_unpublished_answers():
    run = sample_run()
    for n in range(1, 4):
        add_result(run, n)
    run["calls"][-1]["receipt"]["private_marker"] = "never-expose"
    public = public_run(run)
    assert "answer-2" not in json.dumps(public)
    assert "never-expose" not in json.dumps(public)
    assert public["request_count"] == 3
    assert public["billing_count"] is None
    assert public["execution_unknown"] == 0


def test_id_hash_pins_model_and_complete_input():
    packet = make_packet(sample_run(), 1)
    for key in ("model", "effort", "prompt"):
        altered = deepcopy(packet)
        altered[key] += "changed"
        assert call_fingerprint(altered) != packet["call_hash"]


@pytest.mark.parametrize("value", [None, [], {"code": "private-marker"},
    {"code": "cli_exit_nonzero", "exit_code": True}, {"code": "cli_exit_nonzero", "exit_code": "7"},
    {"code": "cli_exit_nonzero", "exit_code": 256}, {"code": "cli_exit_nonzero", "termination_requested": "private-marker"}])
def test_invalid_diagnostic_never_exposes_arbitrary_values(value):
    assert safe_diagnostic(value) is None


def test_diagnostic_projection_strips_extra_fields_and_supports_old_records():
    run = sample_run()
    add_result(run, 1)
    assert public_run(run)["calls"][0]["diagnostic"] is None
    run["calls"][0]["diagnostic"] = {"code": "cli_exit_nonzero", "exit_code": 7,
        "termination_requested": False, "stderr": "private-marker", "prompt": "private-marker"}
    public = public_run(run)
    assert public["calls"][0]["diagnostic"] == {"code": "cli_exit_nonzero", "exit_code": 7,
                                                       "termination_requested": False}
    assert "private-marker" not in json.dumps(public)


@pytest.mark.parametrize("raw,expected", [
    ({"event_type": "item.completed", "item_type": "error", "item_status": "missing", "message": "private-marker"},
     {"event_type": "item.completed", "item_type": "error", "item_status": "missing"}),
    ({"event_type": "private-marker", "item_type": ["private-marker"], "item_status": {"secret": "private-marker"}},
     {"event_type": "unknown", "item_type": "unknown", "item_status": "unknown"}),
    ({}, {"event_type": "missing", "item_type": "missing", "item_status": "missing"}),
    ({"event_type": None, "item_type": False, "item_status": 123},
     {"event_type": "unknown", "item_type": "unknown", "item_status": "unknown"}),
])
def test_safe_event_metadata_reaches_public_projection_with_only_fixed_values(raw, expected):
    value = {"code": "cli_notice_event", "exit_code": 0, "termination_requested": False,
             "event": raw, "stderr": "private-marker"}
    run = sample_run()
    add_result(run, 1)
    run["calls"][0]["diagnostic"] = value
    projected = public_run(run)["calls"][0]["diagnostic"]
    assert projected == {"code": "cli_notice_event", "exit_code": 0, "termination_requested": False, "event": expected}
    assert safe_diagnostic(projected) == projected
    assert "private-marker" not in json.dumps(projected)


@pytest.mark.parametrize("raw", [None, "private-marker", ["private-marker"], 1])
def test_invalid_event_container_does_not_destroy_core_diagnostic(raw):
    base = {"code": "tool_event_rejected", "exit_code": 0, "termination_requested": False}
    assert safe_diagnostic({**base, "event": raw}) == base


def test_notice_kind_is_sanitized_and_old_or_non_notice_records_do_not_gain_it():
    base = {"code": "cli_notice_event", "exit_code": 0, "termination_requested": False}
    event = {"event_type": "item.completed", "item_type": "error", "item_status": "missing"}
    assert safe_diagnostic({**base, "event": event})["event"] == event
    for raw in ("private-marker", {"private": "private-marker"}, None):
        projected = safe_diagnostic({**base, "event": {**event, "message": "private-marker"}, "notice_kind": raw})
        assert projected["event"] == event
        assert projected["notice_kind"] == "unclassified"
        assert "private-marker" not in json.dumps(projected)
    for kind in ("model_reroute_format", "event_stream_lag_format", "requirements_fallback_format", "unclassified"):
        projected = safe_diagnostic({**base, "event": event, "notice_kind": kind})
        assert projected["notice_kind"] == kind
    run = sample_run()
    add_result(run, 1)
    run["calls"][0]["diagnostic"] = {**base, "event": {**event, "message": "private-marker"},
                                      "notice_kind": "event_stream_lag_format"}
    public = public_run(run)["calls"][0]["diagnostic"]
    assert public == {**base, "event": event, "notice_kind": "event_stream_lag_format"}
    assert "private-marker" not in json.dumps(public)
    tool = {**event, "item_type": "command_execution", "notice_kind": "model_reroute_format"}
    assert safe_diagnostic({**base, "event": tool})["event"] == {k: v for k, v in tool.items() if k != "notice_kind"}


def test_notice_source_is_sanitized_and_projected_without_private_text():
    base = {"code": "cli_notice_event", "exit_code": 0, "termination_requested": True}
    for source in ("config_warning", "warning", "deprecation_notice", "model_rerouted",
                   "exec_warning", "unavailable", "unknown"):
        assert safe_diagnostic({**base, "notice_source": source})["notice_source"] == source
    for source in ("private-marker", {"private": "private-marker"}, None):
        projected = safe_diagnostic({**base, "notice_source": source, "message": "private-marker"})
        assert projected["notice_source"] == "unknown"
        assert "private-marker" not in json.dumps(projected)
    assert "notice_source" not in safe_diagnostic(base)
    assert "notice_source" not in safe_diagnostic({**base, "code": "tool_event_rejected", "notice_source": "warning"})
    run = sample_run()
    add_result(run, 1)
    run["calls"][0]["diagnostic"] = {**base, "notice_source": "warning", "message": "private-marker"}
    assert public_run(run)["calls"][0]["diagnostic"] == {**base, "notice_source": "warning"}


def test_grok_error_name_is_an_identifier_and_only_on_cli_error_event():
    base = {"code": "cli_error_event", "exit_code": -15, "termination_requested": True}
    assert safe_diagnostic({**base, "error_name": "MessageAbortedError",
                            "message": "private-marker"})["error_name"] == "MessageAbortedError"
    projected = safe_diagnostic({**base, "error_name": "private marker!!", "message": "private-marker"})
    assert projected["error_name"] == "invalid"
    assert "private-marker" not in json.dumps(projected)
    assert "private marker!!" not in json.dumps(projected)
    assert "error_name" not in safe_diagnostic(base)
    assert "error_name" not in safe_diagnostic({**base, "error_name": None})
    assert "error_name" not in safe_diagnostic({**base, "code": "cli_notice_event",
                                                "error_name": "MessageAbortedError"})
    assert DiscussionDiagnosticError("cli_error_event", error_name="private marker!!").error_name == "invalid"
    assert DiscussionDiagnosticError("cli_error_event").error_name is None
    assert DiscussionDiagnosticError("cli_notice_event", error_name="MessageAbortedError").error_name is None
    run = sample_run()
    add_result(run, 1)
    run["calls"][0]["diagnostic"] = {**base, "error_name": "MessageAbortedError", "message": "private-marker"}
    assert public_run(run)["calls"][0]["diagnostic"] == {**base, "error_name": "MessageAbortedError"}
    run["calls"][0]["diagnostic"] = {**base, "code": "prepare_failed", "error_name": "MessageAbortedError"}
    assert "error_name" not in public_run(run)["calls"][0]["diagnostic"]


def claude_hosted_run():
    run = sample_run()
    run["host_provider"] = "claude_code"
    return run


def test_codex_host_packet_keeps_its_exact_shape_and_prompt():
    run = sample_run()
    before = make_packet(run, 1)
    run["host_provider"] = "codex"
    after = make_packet(run, 1)
    assert "host_provider" not in after
    assert after["prompt"] == before["prompt"] and after["call_hash"] == before["call_hash"]
    assert "調度員與 Codex 是不同席位" in after["prompt"]
    assert "3,500 bytes" not in after["prompt"]


@pytest.mark.parametrize("ordinal", [1, 5, 9])
def test_claude_host_packet_routes_to_claude_and_limits_output(ordinal):
    run = claude_hosted_run()
    for number in range(1, ordinal):
        add_result(run, number)
    packet = make_packet(run, ordinal)
    assert packet["host_provider"] == "claude_code" and packet["speaker"] == "dispatcher"
    assert packet["epoch"] == run["bridge_epochs"]["claude_code"]
    assert "調度員與 Claude Code 是不同席位" in packet["prompt"]
    assert "不要加 Markdown 程式碼框" in packet["prompt"] and "3,500 bytes" in packet["prompt"]


def test_members_do_not_carry_host_provider_when_claude_hosts():
    run = claude_hosted_run()
    add_result(run, 1)
    packet = make_packet(run, 2)
    assert "host_provider" not in packet and packet["epoch"] == run["bridge_epochs"]["codex"]
    assert "3,500 bytes" not in packet["prompt"]


def test_host_provider_is_part_of_the_call_fingerprint():
    packet = make_packet(claude_hosted_run(), 1)
    assert call_fingerprint(packet) != call_fingerprint({k: v for k, v in packet.items() if k != "host_provider"})
    changed = {**packet, "host_provider": "codex"}
    with pytest.raises(ValueError):
        validate_begin(changed)


@pytest.mark.parametrize("host", ["codex", "grok", "", None])
def test_only_claude_can_be_named_as_alternate_host(host):
    packet = {**make_packet(sample_run(), 1), "host_provider": host}
    packet["call_hash"] = call_fingerprint(packet)
    with pytest.raises(ValueError):
        validate_begin(packet)


def test_host_provider_is_rejected_on_member_packets():
    run = sample_run()
    add_result(run, 1)
    packet = {**make_packet(run, 2), "host_provider": "claude_code"}
    packet["call_hash"] = call_fingerprint(packet)
    with pytest.raises(ValueError):
        validate_begin(packet)


def test_unknown_packet_field_is_still_rejected():
    packet = {**make_packet(sample_run(), 1), "extra": "x"}
    with pytest.raises(ValueError):
        validate_begin(packet)


@pytest.mark.parametrize("first,expected", [(None, ["codex", "claude_code"]), ("", ["codex", "claude_code"]),
                                            ("claude_code", ["claude_code", "codex"]),
                                            ("codex", ["codex", "claude_code"])])
def test_host_order_defaults_to_registration_order(first, expected):
    assert host_order(first) == expected


@pytest.mark.parametrize("first", ["typo", "grok", "claude_code_api"])
def test_host_order_rejects_unregistered_or_non_host_codes(first):
    with pytest.raises(ValueError):
        host_order(first)
