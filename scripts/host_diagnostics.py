"""主機端 CLI 失敗診斷檔：只在私聊回合失敗時寫，只給擁有者看。

決策：失敗時保存經遮罩的 stderr 尾段與事件類型序列，
協助查出 DNS／OAuth／CLI 版本這類根因。界線：

- 只寫本機檔：`$AIOFFICE_DIAG_DIR`（絕對路徑）或 `$XDG_STATE_HOME/ai-office/diag`
  （預設 `~/.local/state/ai-office/diag`）下的 `<provider>/<時間>-<ID>.log`；
  目錄 0700、檔案 0600，不跟隨符號連結，超過 7 天的檔案在下次寫入時刪除。
- 不經 socket 回傳、不進 App 或資料庫；對外只多一句「診斷 ID」，讓擁有者找到檔案。
- stdout 只取 JSON 事件的類型名稱（固定格式），不寫回覆正文；stderr 與 argv 先遮罩再寫。
- 群聊回覆被判無效時，只多記回覆的形狀與位元組數（`reply_shape`），同樣不寫正文。
- Claude 另外記錯誤類別（`claude_error_class`）：只取事件裡的固定欄位，分得出額度、認證與 API 錯誤，同樣不寫正文。
- 任何寫入失敗都回傳 None，不影響原本的錯誤處理。
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import secrets
import shlex
import stat
import time

DIAG_ENV = "AIOFFICE_DIAG_DIR"
RETENTION_SECONDS = 7 * 24 * 3600
TAIL_LIMIT = 64 * 1024
EVENT_LIMIT = 200
TAIL_ATTRIBUTE = "_office_output_tails"
MASK = "[已遮罩]"
_EVENT_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{0,63}")
_PROVIDER = re.compile(r"[a-z][a-z0-9_]{0,31}")
_REPLY_SHAPE = re.compile(r"not_text [A-Za-z]+|not_utf8|(?:text|blank) [0-9]+ bytes")
# event_rejected／stream_failed 供群聊執行器（discussion_host）使用：事件守門中止、或讀寫串流與程序核對失敗。
_REASONS = frozenset({"timeout", "exit_nonzero", "parse_failed", "oversize", "event_rejected", "stream_failed"})

# 順序有意義：先處理帶前綴的值，再處理通用的長字串。
_PATTERNS = (
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+"), "Bearer " + MASK),
    (re.compile(r"(?i)\b(authorization|cookie|set-cookie)(\s*[:=]\s*)[^\r\n]+"), r"\1\2" + MASK),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}"), MASK),
    (re.compile(r"\b(?:sk-|xai-|ghp_|gho_|ghu_|ghs_|github_pat_|glpat-|ya29\.|AIza)[A-Za-z0-9._\-]{8,}"), MASK),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), MASK),
    (re.compile(r"(?i)\b([A-Za-z0-9_-]*(?:token|secret|password|passwd|api[_-]?key|access[_-]?key|credential|auth)"
                r"[A-Za-z0-9_-]*)(\s*[=:]\s*)(\"[^\"]*\"|'[^']*'|[^\s,;&]+)"), r"\1\2" + MASK),
    (re.compile(r"(https?://[^\s?#]+)\?[^\s#]*"), r"\1?" + MASK),
    (re.compile(r"(https?://)[^\s/:@]+:[^\s/@]+@"), r"\1" + MASK + "@"),
    (re.compile(r"[A-Za-z0-9+/_-]{40,}={0,2}"), MASK),
)


def mask(text: str) -> str:
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def diag_root() -> Path:
    value = os.environ.get(DIAG_ENV)
    if value and Path(value).is_absolute():
        return Path(value)
    state = os.environ.get("XDG_STATE_HOME")
    base = Path(state) if state and Path(state).is_absolute() else Path.home() / ".local" / "state"
    return base / "ai-office" / "diag"


def tail_buffers(process) -> dict:
    """private_cli 在讀取迴圈裡把 stdout／stderr 各自最後 64 KiB 記在 process 上；逾時時也拿得到。"""
    value = getattr(process, TAIL_ATTRIBUTE, None)
    return value if isinstance(value, dict) else {}


def event_types(stdout_tail: bytes) -> list[str]:
    """只取 JSON 事件的類型（含 item／part 子類型），不取任何其他欄位。"""
    names = []
    for raw in stdout_tail.splitlines():
        try:
            event = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            continue
        if not isinstance(event, dict) or not isinstance(event.get("type"), str):
            continue
        name = event["type"]
        for key in ("item", "part"):
            inner = event.get(key)
            if isinstance(inner, dict) and isinstance(inner.get("type"), str):
                name = f"{name}/{inner['type']}"
                break
        else:
            if isinstance(event.get("subtype"), str):
                name = f"{name}/{event['subtype']}"
        names.append(name if all(_EVENT_NAME.fullmatch(part) for part in name.split("/")) else "invalid")
    return names[-EVENT_LIMIT:]


def _error_token(value) -> str:
    """錯誤類別的值只能是布林、HTTP 狀態碼或短識別字；其他一律寫 invalid，不寫原值。"""
    if isinstance(value, bool):
        return "true" if value else "false"
    if type(value) is int:
        return str(value) if 0 <= value <= 999 else "invalid"
    return mask(value) if isinstance(value, str) and _EVENT_NAME.fullmatch(value) else "invalid"


def claude_error_class(stdout_tail: bytes) -> str:
    """Claude 事件裡的錯誤類別，同一欄位取最後一次的值；不取 message、result 等任何含正文的欄位。"""
    found: dict[str, str] = {}

    def keep(name, value):
        if value is not None:
            found[name] = _error_token(value)

    for raw in stdout_tail.splitlines():
        try:
            event = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            continue
        if not isinstance(event, dict):
            continue
        kind = event.get("type")
        if kind == "assistant":
            keep("assistant.error", event.get("error"))
            keep("assistant.api_error_status", event.get("api_error_status"))
        elif kind == "system" and event.get("subtype") == "api_retry":
            keep("retry.error", event.get("error"))
            keep("retry.status", event.get("error_status"))
        elif kind == "rate_limit_event" and isinstance(event.get("rate_limit_info"), dict):
            keep("rate_limit.status", event["rate_limit_info"].get("status"))
            keep("rate_limit.type", event["rate_limit_info"].get("rateLimitType"))
        elif kind == "result":
            for key in ("is_error", "subtype", "api_error_status", "api_error_code", "terminal_reason"):
                keep(f"result.{key}", event.get(key))
    return " ".join(f"{name}={value}" for name, value in found.items())


def reply_shape(content) -> str:
    """描述回覆的形狀而不含正文，讓 reply_invalid 分得出不是文字、無法編碼、空白與超過上限。"""
    if not isinstance(content, str):
        return f"not_text {type(content).__name__}"
    try:
        size = len(content.encode())
    except UnicodeEncodeError:
        return "not_utf8"
    return f"{'text' if content.strip() else 'blank'} {size} bytes"


def _private_dir(path: Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.lstat()
    if (stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700):
        raise OSError("diagnostic directory is not private")


def _prune(directory: Path, now: float) -> None:
    for entry in directory.iterdir():
        try:
            info = entry.lstat()
        except FileNotFoundError:
            continue
        if (entry.suffix == ".log" and stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                and now - info.st_mtime > RETENTION_SECONDS):
            entry.unlink(missing_ok=True)


def record(provider: str, *, process, argv, reason: str, started: float,
           root: Path | None = None, clock=time.time, detail: str | None = None,
           reply: str | None = None) -> str | None:
    """寫一份診斷檔並回傳診斷 ID；任何問題都回傳 None，不拋例外。

    detail 只接受固定代碼形狀（例如群聊的 cli_error_event）；reply 只接受 reply_shape 的輸出；其他值不寫入。
    """
    try:
        if not _PROVIDER.fullmatch(provider) or reason not in _REASONS:
            return None
        directory = (root or diag_root()) / provider
        _private_dir(directory.parent)
        _private_dir(directory)
        now = clock()
        _prune(directory, now)
        tails = tail_buffers(process)
        stdout_tail = bytes(tails.get("stdout", b""))[-TAIL_LIMIT:]
        stderr_tail = bytes(tails.get("stderr", b""))[-TAIL_LIMIT:]
        events = event_types(stdout_tail)
        error_class = claude_error_class(stdout_tail) if provider == "claude_code" else ""
        exit_code = getattr(process, "returncode", None)
        identifier = secrets.token_hex(6)
        stamp = time.strftime("%Y%m%dT%H%M%S", time.localtime(now))
        body = "\n".join([
            f"provider: {provider}",
            f"diagnostic_id: {identifier}",
            f"reason: {reason}",
            *([f"detail: {detail}"] if isinstance(detail, str) and _EVENT_NAME.fullmatch(detail) else []),
            *([f"reply: {reply}"] if isinstance(reply, str) and _REPLY_SHAPE.fullmatch(reply) else []),
            *([f"error_class: {error_class}"] if error_class else []),
            f"time:{time.strftime('%Y-%m-%dT%H:%M:%S%z', time.localtime(now))}",
            f"elapsed_seconds: {max(0, round(time.monotonic() - started, 1))}",
            f"exit_code: {exit_code if isinstance(exit_code, int) else 'unknown'}",
            "argv: " + mask(shlex.join(str(arg) for arg in argv)),
            f"events ({len(events)}, last {EVENT_LIMIT} at most): " + " ".join(events),
            f"--- stderr tail (masked, last {TAIL_LIMIT // 1024} KiB) ---",
            mask(stderr_tail.decode("utf-8", errors="replace")),
            "",
        ])
        path = directory / f"{stamp}-{identifier}.log"
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(body)
        return identifier
    except (OSError, ValueError, TypeError):
        return None


def failure(message: str, provider: str, **details) -> str:
    """寫診斷檔並把 ID 附在固定錯誤訊息後面；沒寫成就回傳原訊息。"""
    identifier = record(provider, **details)
    return f"{message}（診斷 ID：{identifier}）" if identifier else message
