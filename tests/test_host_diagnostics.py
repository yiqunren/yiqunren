"""主機端失敗診斷檔：遮罩、只取事件類型、權限、保留天數。

全部離線：假 CLI 與暫存目錄。
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import stat
import sys
import time
from types import SimpleNamespace

import pytest

from scripts import host_diagnostics, private_cli

SECRETS = {
    "bearer": "Authorization: Bearer abcdefghijklmnop123456",
    "openai": "key sk-proj-ABCDEFGHIJKLMNOPQRSTUV",
    "xai": "xai-ABCDEFGHIJKLMNOPQRSTUVWX",
    "jwt": "token eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
    "query": "GET https://auth.example.com/callback?code=abc123&state=xyz HTTP/1.1",
    "kv": "api_key=plainsecretvalue password: hunter2",
    "aws": "AKIAABCDEFGHIJKLMNOP",
    "long": "Q" * 48,
    "userinfo": "https://user:pass@example.com/path",
}
VALUES = ("abcdefghijklmnop123456", "sk-proj-ABCDEFGHIJKLMNOPQRSTUV", "xai-ABCDEFGHIJKLMNOPQRSTUVWX",
          "eyJhbGciOiJIUzI1NiJ9", "code=abc123", "plainsecretvalue", "hunter2", "AKIAABCDEFGHIJKLMNOP",
          "Q" * 48, "user:pass")


def test_mask_removes_credentials_but_keeps_diagnostic_text():
    text = "\n".join(SECRETS.values()) + "\ngetaddrinfo failed: Temporary failure in name resolution (api.openai.com)"
    masked = host_diagnostics.mask(text)
    for value in VALUES:
        assert value not in masked, value
    assert "Temporary failure in name resolution (api.openai.com)" in masked
    assert "https://auth.example.com/callback?" in masked


def test_event_types_keep_only_type_names():
    lines = [
        {"type": "thread.started", "thread_id": "secret-thread"},
        {"type": "item.completed", "item": {"type": "command_execution", "command": "cat ~/.ssh/id_rsa"}},
        {"type": "system", "subtype": "init", "tools": ["Read"]},
        {"type": "tool_use", "part": {"type": "tool", "state": {"input": "secret"}}},
        {"type": "weird type with spaces"},
        {"no_type": True},
    ]
    raw = b"\n".join(json.dumps(line).encode() for line in lines) + b"\nnot json\n"
    assert host_diagnostics.event_types(raw) == [
        "thread.started", "item.completed/command_execution", "system/init", "tool_use/tool", "invalid"]
    many = b"\n".join(json.dumps({"type": f"e{i}"}).encode() for i in range(500))
    assert len(host_diagnostics.event_types(many)) == host_diagnostics.EVENT_LIMIT


def fake_process(stdout=b"", stderr=b"", returncode=1):
    process = SimpleNamespace(returncode=returncode)
    setattr(process, host_diagnostics.TAIL_ATTRIBUTE, {"stdout": bytearray(stdout), "stderr": bytearray(stderr)})
    return process


def test_record_writes_private_masked_file_without_reply_text(tmp_path):
    stdout = json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "PRIVATE REPLY"}}).encode()
    process = fake_process(stdout=stdout + b"\n", stderr=("boom " + SECRETS["bearer"]).encode())
    identifier = host_diagnostics.record("codex", process=process, argv=["codex", "exec", "--model", "gpt-6-sol"],
                                         reason="exit_nonzero", started=time.monotonic(), root=tmp_path)
    assert identifier and len(identifier) == 12
    files = list((tmp_path / "codex").glob(f"*-{identifier}.log"))
    assert len(files) == 1
    body = files[0].read_text(encoding="utf-8")
    assert stat.S_IMODE(files[0].stat().st_mode) == 0o600
    assert stat.S_IMODE((tmp_path / "codex").stat().st_mode) == 0o700
    assert "reason: exit_nonzero" in body and "exit_code: 1" in body and "item.completed/agent_message" in body
    assert "argv: codex exec --model gpt-6-sol" in body
    assert "PRIVATE REPLY" not in body and "abcdefghijklmnop123456" not in body and "boom" in body


def test_record_keeps_only_the_last_64_kib_of_stderr(tmp_path):
    stderr = b"HEAD-MARKER " + b"x " * 40_000 + b" TAIL-MARKER"
    identifier = host_diagnostics.record("grok", process=fake_process(stderr=stderr), argv=["kilo"],
                                         reason="timeout", started=time.monotonic(), root=tmp_path)
    body = next((tmp_path / "grok").glob("*.log")).read_text(encoding="utf-8")
    assert identifier and "TAIL-MARKER" in body and "HEAD-MARKER" not in body


@pytest.mark.parametrize("reason", ["event_rejected", "stream_failed"])
def test_discussion_reasons_and_detail_accept_only_fixed_code_shapes(tmp_path, reason):
    good = host_diagnostics.record("grok", process=fake_process(), argv=["kilo"], reason=reason,
                                   started=time.monotonic(), root=tmp_path, detail="cli_error_event")
    bad = host_diagnostics.record("codex", process=fake_process(), argv=["codex"], reason=reason,
                                  started=time.monotonic(), root=tmp_path, detail="free text\nreason: forged")
    grok = next((tmp_path / "grok").glob("*.log")).read_text(encoding="utf-8")
    codex = next((tmp_path / "codex").glob("*.log")).read_text(encoding="utf-8")
    assert good and bad and f"reason: {reason}\ndetail: cli_error_event\n" in grok
    assert "detail:" not in codex and "forged" not in codex


@pytest.mark.parametrize("content,shape", [
    ("字" * 2000, "text 6000 bytes"), ("短回覆", "text 9 bytes"), ("", "blank 0 bytes"), (" \n", "blank 2 bytes"),
    (None, "not_text NoneType"), (["x"], "not_text list"), ("\ud800", "not_utf8"),
])
def test_reply_shape_describes_the_reply_without_its_text(content, shape):
    assert host_diagnostics.reply_shape(content) == shape


def test_record_accepts_only_reply_shapes(tmp_path):
    common = {"process": fake_process(), "reason": "parse_failed", "started": time.monotonic(), "root": tmp_path,
              "detail": "reply_invalid"}
    good = host_diagnostics.record("claude_code", argv=["claude"], reply="text 6000 bytes", **common)
    bad = host_diagnostics.record("codex", argv=["codex"], reply="PRIVATE REPLY\nreason: forged", **common)
    claude = next((tmp_path / "claude_code").glob("*.log")).read_text(encoding="utf-8")
    codex = next((tmp_path / "codex").glob("*.log")).read_text(encoding="utf-8")
    assert good and bad and "detail: reply_invalid\nreply: text 6000 bytes\n" in claude
    assert "reply:" not in codex and "PRIVATE REPLY" not in codex and "forged" not in codex


def claude_failure_events(**overrides):
    events = [
        {"type": "system", "subtype": "init", "session_id": "s", "tools": ["Read"]},
        {"type": "system", "subtype": "api_retry", "attempt": 1, "error": "overloaded", "error_status": 529},
        {"type": "rate_limit_event", "rate_limit_info": {"status": "allowed_warning", "rateLimitType": "seven_day",
                                                         "utilization": 0.9, "resetsAt": 1800000000}},
        {"type": "assistant", "error": "authentication_failed", "api_error_status": 401,
         "message": {"content": [{"type": "text", "text": "PRIVATE REPLY"}]}},
        {"type": "result", "subtype": "success", "is_error": True, "result": "PRIVATE REPLY", "session_id": "s",
         "api_error_status": 401, "api_error_code": "invalid_token", "terminal_reason": "model_error", **overrides},
    ]
    return "\n".join(json.dumps(event) for event in events).encode()


def test_claude_error_class_reads_only_the_fixed_fields():
    assert host_diagnostics.claude_error_class(claude_failure_events()) == (
        "retry.error=overloaded retry.status=529 rate_limit.status=allowed_warning rate_limit.type=seven_day "
        "assistant.error=authentication_failed assistant.api_error_status=401 result.is_error=true "
        "result.subtype=success result.api_error_status=401 result.api_error_code=invalid_token "
        "result.terminal_reason=model_error")


def test_claude_error_class_keeps_the_last_value_of_a_field():
    raw = "\n".join(json.dumps({"type": "assistant", "error": name}) for name in ("rate_limit", "server_error")).encode()
    assert host_diagnostics.claude_error_class(raw) == "assistant.error=server_error"


def test_claude_error_class_reads_the_single_json_output():
    raw = json.dumps({"type": "result", "subtype": "error_during_execution", "is_error": True}).encode()
    assert host_diagnostics.claude_error_class(raw) == "result.is_error=true result.subtype=error_during_execution"


@pytest.mark.parametrize("value", ["PRIVATE REPLY", "line\nreason: forged", "x" * 200, {"text": "PRIVATE"}, ["PRIVATE"],
                                   1.5, -1, 1000])
def test_claude_error_class_never_copies_unexpected_values(value):
    line = host_diagnostics.claude_error_class(claude_failure_events(api_error_code=value))
    assert "result.api_error_code=invalid" in line
    assert "PRIVATE" not in line and "forged" not in line and "\n" not in line


def test_claude_error_class_masks_a_secret_shaped_identifier():
    secret = "sk-proj-ABCDEFGHIJKLMNOPQRSTUV"
    line = host_diagnostics.claude_error_class(claude_failure_events(api_error_code=secret))
    assert secret not in line and host_diagnostics.MASK in line


@pytest.mark.parametrize("raw", [b"", b"not json\n", b"[1]\n", b'{"type": "system", "subtype": "init"}\n',
                                 b'{"type": "rate_limit_event", "rate_limit_info": "text"}\n', b"\xff\xfe\n"])
def test_claude_error_class_is_empty_without_error_fields(raw):
    assert host_diagnostics.claude_error_class(raw) == ""


def test_record_writes_error_class_for_claude_only(tmp_path):
    common = {"process": fake_process(stdout=claude_failure_events()), "reason": "exit_nonzero",
              "started": time.monotonic(), "root": tmp_path}
    assert host_diagnostics.record("claude_code", argv=["claude"], **common)
    assert host_diagnostics.record("codex", argv=["codex"], **common)
    claude = next((tmp_path / "claude_code").glob("*.log")).read_text(encoding="utf-8")
    codex = next((tmp_path / "codex").glob("*.log")).read_text(encoding="utf-8")
    assert "\nerror_class: retry.error=overloaded " in claude and "PRIVATE REPLY" not in claude
    assert "error_class" not in codex


def test_record_omits_error_class_when_there_is_nothing_to_report(tmp_path):
    assert host_diagnostics.record("claude_code", process=fake_process(stdout=b""), argv=["claude"],
                                   reason="exit_nonzero", started=time.monotonic(), root=tmp_path)
    assert "error_class" not in next((tmp_path / "claude_code").glob("*.log")).read_text(encoding="utf-8")


def test_record_prunes_week_old_files_and_ignores_symlinks(tmp_path):
    directory = tmp_path / "claude_code"
    directory.mkdir(mode=0o700, parents=True)
    tmp_path.chmod(0o700)
    old, recent = directory / "old.log", directory / "recent.log"
    old.write_text("old"); recent.write_text("recent")
    week_ago = time.time() - host_diagnostics.RETENTION_SECONDS - 60
    os.utime(old, (week_ago, week_ago))
    target = tmp_path / "outside.log"
    target.write_text("keep me")
    os.utime(target, (week_ago, week_ago))
    (directory / "link.log").symlink_to(target)
    assert host_diagnostics.record("claude_code", process=fake_process(), argv=["claude"], reason="timeout",
                                   started=time.monotonic(), root=tmp_path)
    assert not old.exists() and recent.exists() and target.exists() and (directory / "link.log").is_symlink()


def test_record_refuses_unsafe_directories_without_raising(tmp_path):
    loose = tmp_path / "loose"
    (loose / "codex").mkdir(parents=True)
    loose.chmod(0o700)
    (loose / "codex").chmod(0o755)
    assert host_diagnostics.record("codex", process=fake_process(), argv=["codex"], reason="timeout",
                                   started=time.monotonic(), root=loose) is None
    assert not list((loose / "codex").iterdir())
    real = tmp_path / "real"
    real.mkdir(mode=0o700)
    linked = tmp_path / "linked"
    linked.symlink_to(real, target_is_directory=True)
    assert host_diagnostics.record("codex", process=fake_process(), argv=["codex"], reason="timeout",
                                   started=time.monotonic(), root=linked) is None
    blocker = tmp_path / "file-root"
    blocker.write_text("not a directory")
    assert host_diagnostics.record("codex", process=fake_process(), argv=["codex"], reason="timeout",
                                   started=time.monotonic(), root=blocker) is None
    assert host_diagnostics.record("../escape", process=fake_process(), argv=[], reason="timeout",
                                   started=time.monotonic(), root=tmp_path) is None
    assert host_diagnostics.record("codex", process=fake_process(), argv=[], reason="made-up",
                                   started=time.monotonic(), root=tmp_path) is None


def test_failure_appends_the_id_only_when_a_file_was_written(tmp_path):
    message = host_diagnostics.failure("Codex timed out", "codex", process=fake_process(), argv=["codex"],
                                       reason="timeout", started=time.monotonic(), root=tmp_path)
    assert message.startswith("Codex timed out（診斷 ID：") and message.endswith("）")
    blocker = tmp_path / "blocked"
    blocker.write_text("x")
    assert host_diagnostics.failure("Codex timed out", "codex", process=fake_process(), argv=["codex"],
                                    reason="timeout", started=time.monotonic(), root=blocker) == "Codex timed out"


def test_diag_root_uses_absolute_override_only(monkeypatch, tmp_path):
    monkeypatch.setenv("AIOFFICE_DIAG_DIR", str(tmp_path / "diag"))
    assert host_diagnostics.diag_root() == tmp_path / "diag"
    monkeypatch.setenv("AIOFFICE_DIAG_DIR", "relative/diag")
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    assert host_diagnostics.diag_root() == tmp_path / "state" / "ai-office" / "diag"
    monkeypatch.delenv("AIOFFICE_DIAG_DIR")
    monkeypatch.delenv("XDG_STATE_HOME")
    assert host_diagnostics.diag_root() == Path.home() / ".local" / "state" / "ai-office" / "diag"


def spawn(script):
    return asyncio.create_subprocess_exec(
        sys.executable, "-c", script, start_new_session=True,
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)


def test_private_cli_keeps_output_tails_even_when_the_turn_times_out(monkeypatch):
    monkeypatch.setattr(private_cli, "TERMINATE_GRACE", 0.5)
    script = ("import sys, time\nsys.stdin.read()\n"
              "sys.stderr.write('E' * 100000 + 'STDERR-END'); sys.stderr.flush()\n"
              "sys.stdout.write('{\"type\": \"turn.started\"}\\n'); sys.stdout.flush()\n"
              "time.sleep(30)\n")

    async def run():
        process = await spawn(script)
        with pytest.raises(asyncio.TimeoutError):
            await private_cli.communicate_private(process, b"x", 1.5)
        return host_diagnostics.tail_buffers(process)

    tails = asyncio.run(run())
    assert len(tails["stderr"]) == host_diagnostics.TAIL_LIMIT and tails["stderr"].endswith(b"STDERR-END")
    assert bytes(tails["stdout"]) == b'{"type": "turn.started"}\n'


