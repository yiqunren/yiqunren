"""Claude Code 橋接（API key 模式，SPEC NFR-7）：另外啟動的本機程序，用 Unix socket 接後端的回合協定。

啟動：在 repo 根目錄執行 `python -m scripts.claude_bridge`。後端設定 YIQUNREN_BRIDGES=claude_code 才會連過來。

- 認證：只用環境變數 ANTHROPIC_API_KEY；沒設就拒絕啟動。只檢查有沒有值，不讀出、不存、不記錄。
- 每一回合跑一次 `claude --bare -p`：不載入 hooks、skills、plugins、MCP、CLAUDE.md 與 auto memory；
  訊息從 stdin 送進去，工作目錄是這段對話的工作區（後端建在狀態目錄的 workspaces/ 下）。
- 權限：acceptEdits 讓它在工作區內新增、修改檔案；會執行指令的工具（Bash、Monitor、PowerShell）整個禁用
  （acceptEdits 會自動核准常見的檔案指令）；
  設定檔加上禁止讀寫工作區以外的路徑；其他需要核准的動作在 -p 模式一律被拒。
- 續接：後端送來上一個完成回合的 session_id 時用 --resume；回覆時帶回這一回合的 session_id。
- 失敗：結果不是 success 一律算失敗，寫一份診斷檔（scripts/host_diagnostics.py），錯誤訊息只帶診斷 ID。
- 寫入權：整個 CLI 執行期間對工作區登記寫入權（NFR-2，經 scripts/turn_host.py 的 guard）。

環境變數：YIQUNREN_CLAUDE_BIN（claude 執行檔的絕對路徑，沒設時從 PATH 找）、YIQUNREN_CLAUDE_CODE_SOCKET、
YIQUNREN_CLAUDE_CODE_MAX_TIMEOUT（單回合上限秒數）、YIQUNREN_STATE_DIR（要和後端相同）。
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import stat
import sys
import time
import uuid

from app.services import adapters
from app.services import turn_contract as contract
from app.storage import workspaces
from app.web import config
from scripts import host_diagnostics, private_cli, turn_host

PROVIDER = 'claude_code'
KEY_ENV = 'ANTHROPIC_API_KEY'
BIN_ENV = 'YIQUNREN_CLAUDE_BIN'
TIMEOUT_ENV = 'YIQUNREN_CLAUDE_CODE_MAX_TIMEOUT'
EFFORTS = frozenset({'low', 'medium', 'high', 'xhigh', 'max'})
MODEL = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:\[\]-]{0,99}')
SESSION = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
MAX_BUDGET_USD = 1000
# 回覆經 JSON 編碼後的上限（位元組）：後端單行回覆上限是 120,000（app/services/cli_socket.py），留空間給其他欄位。
# 超過 100,000 位元組但沒超過這裡的回覆照常交出，由後端判為「回覆過長」（FR-2）。
MAX_ENCODED_REPLY = 115_000
REQUEST_LIMIT = 1_000_000
# 會執行指令的內建工具（官方工具清單 code.claude.com/docs/en/tools-reference，2026-11-15 查）：
# Monitor 雖然套用 Bash 的規則，仍明確列出，不依賴這個連動。
COMMAND_TOOLS = ('Bash', 'Monitor', 'PowerShell')
# 權限設定（Claude Code 設定檔格式）：禁止讀寫工作目錄以外的路徑。
SETTINGS = json.dumps({'permissions': {'blockReadsOutsideWorkingDirectories': True,
                                       'blockWritesOutsideWorkingDirectories': True}}, separators=(',', ':'))

FAILED = 'Claude Code 回合失敗'
TIMED_OUT = 'Claude Code 回合逾時'
OVERSIZE = 'Claude Code 輸出超過上限'
REPLY_OVERSIZE = 'Claude Code 回覆超過橋接可傳回的上限'


class StartupError(RuntimeError):
    pass


def find_binary(env=None) -> str:
    env = os.environ if env is None else env
    value = env.get(BIN_ENV, '')
    if value:
        if not Path(value).is_absolute():
            raise StartupError(f'{BIN_ENV} 必須是絕對路徑')
        found = value if os.access(value, os.X_OK) and Path(value).is_file() else None
    else:
        found = shutil.which('claude', path=env.get('PATH'))
    if not found:
        raise StartupError(f'找不到 claude 執行檔，請安裝 Claude Code 或設定 {BIN_ENV}')
    return found


def check_key(env=None) -> None:
    """只檢查有沒有值，不讀出、不記錄。"""
    env = os.environ if env is None else env
    if not env.get(KEY_ENV):
        raise StartupError(f'沒有設定 {KEY_ENV}，Claude Code 橋接只支援 API key 模式')


def make_validate(root: Path):
    def validate(fields: dict, auth_mode: str) -> dict:
        if auth_mode != 'api_key':
            raise ValueError('只支援 API key 模式')
        message, session, model = fields['message'], fields['session_id'], fields['model']
        effort, budget = fields['effort'], fields['max_budget_usd']
        if not isinstance(message, str) or not message.strip():
            raise ValueError('訊息無效')
        if session is not None and (not isinstance(session, str) or not SESSION.fullmatch(session)):
            raise ValueError('session_id 無效')
        if model is not None and (not isinstance(model, str) or not MODEL.fullmatch(model)):
            raise ValueError('模型名稱無效')
        if effort is not None and effort not in EFFORTS:
            raise ValueError('effort 無效')
        if budget is not None and (isinstance(budget, bool) or not isinstance(budget, (int, float))
                                   or not 0 < budget <= MAX_BUDGET_USD):
            raise ValueError('max_budget_usd 無效')
        if not isinstance(fields['workspace'], str):
            raise ValueError('工作區無效')
        workspace = workspaces.check(fields['workspace'], root)  # 必須是狀態目錄 workspaces/ 下、後端建好的目錄
        return {'message': message, 'session': session, 'model': model, 'effort': effort,
                'budget': budget, 'workspace': str(workspace)}
    return validate


def command(binary: str, fields: dict) -> list[str]:
    argv = [binary, '--bare', '-p', '--output-format', 'stream-json', '--verbose',
            '--permission-mode', 'acceptEdits', '--disallowedTools', *COMMAND_TOOLS, '--settings', SETTINGS]
    if fields['model'] is not None:
        argv += ['--model', fields['model']]
    if fields['effort'] is not None:
        argv += ['--effort', fields['effort']]
    if fields['budget'] is not None:
        argv += ['--max-budget-usd', str(fields['budget'])]
    if fields['session'] is not None:
        argv += ['--resume', fields['session']]
    return argv


def progress_items(line: bytes) -> list[dict]:
    """assistant 事件裡的工具呼叫 → 進度項（只取工具名稱）；其他事件不回報。"""
    try:
        event = json.loads(line)
    except (UnicodeDecodeError, ValueError):
        return []
    message = event.get('message') if isinstance(event, dict) and event.get('type') == 'assistant' else None
    content = message.get('content') if isinstance(message, dict) else None
    items = []
    for block in content if isinstance(content, list) else ():
        if isinstance(block, dict) and block.get('type') == 'tool_use' and isinstance(block.get('name'), str):
            name = block['name'][:40]
            if name:
                items.append({'kind': 'item', 'event': 'started', 'item_type': name})
    return items


def final_result(stdout: bytes) -> dict | None:
    """最後一個 result 事件；沒有就回 None。"""
    found = None
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except (UnicodeDecodeError, ValueError):
            continue
        if isinstance(event, dict) and event.get('type') == 'result':
            found = event
    return found


def make_run(binary: str):
    async def run(fields: dict, progress, guard) -> dict:
        holder = f'{PROVIDER}:{uuid.uuid4()}'

        async def operation():
            return await invoke(binary, fields, progress)

        return await guard(fields['workspace'], holder, operation)
    return run


async def invoke(binary: str, fields: dict, progress) -> dict:
    argv = command(binary, fields)
    started = time.monotonic()
    process = await asyncio.create_subprocess_exec(
        *argv, cwd=fields['workspace'], stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE, start_new_session=True)

    def failure(message, reason):
        return RuntimeError(host_diagnostics.failure(message, PROVIDER, process=process, argv=argv,
                                                     reason=reason, started=started))

    def on_line(line: bytes) -> None:
        for item in progress_items(line):
            progress(item)

    try:
        stdout, _ = await private_cli.communicate_private(process, fields['message'].encode('utf-8'),
                                                          contract.TIMEOUT_MAX, on_stdout_line=on_line)
    except asyncio.TimeoutError:
        raise failure(TIMED_OUT, 'timeout') from None
    except RuntimeError as exc:
        if str(exc).startswith('私聊 CLI 輸出超過'):
            raise failure(OVERSIZE, 'oversize') from None
        raise  # 停止狀態未知等，turn_host 依訊息判斷
    if process.returncode != 0:
        raise failure(FAILED, 'exit_nonzero')
    event = final_result(stdout)
    if (event is None or event.get('subtype') != 'success' or event.get('is_error') is not False
            or not isinstance(event.get('result'), str)):
        raise failure(FAILED, 'parse_failed')
    content = event['result']
    if len(json.dumps(content, ensure_ascii=False).encode('utf-8')) > MAX_ENCODED_REPLY:
        raise failure(REPLY_OVERSIZE, 'oversize')
    session = event.get('session_id')
    return {'content': content, 'session': session if isinstance(session, str) and SESSION.fullmatch(session) else None}


# ---- socket 伺服器 ----

def prepare_socket(path: Path) -> None:
    """socket 目錄 0700、自己擁有；留下的舊 socket 沒有人在聽才刪掉，有人在聽就拒絕啟動。"""
    directory = path.parent
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise StartupError('socket 目錄必須是自己擁有、權限 0700 的目錄')
    try:
        info = path.lstat()
    except FileNotFoundError:
        return
    if not stat.S_ISSOCK(info.st_mode):
        raise StartupError('socket 路徑已有其他檔案')
    probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        probe.connect(str(path))
    except (ConnectionRefusedError, FileNotFoundError):
        path.unlink(missing_ok=True)
        return
    finally:
        probe.close()
    raise StartupError('已有橋接在這個 socket 上執行')


def make_client(host: turn_host.TurnHost):
    async def client(reader, writer):
        try:
            line = await reader.readline()
            try:
                reply = await host.handle(json.loads(line))
            except ValueError:
                reply = {'ok': False, 'error': host.invalid}
            except RuntimeError as exc:
                reply = {'ok': False, 'error': str(exc)[:contract.MAX_ERROR_CHARS]}
            except Exception:
                reply = {'ok': False, 'error': host.failed}
            writer.write((json.dumps(reply, ensure_ascii=False) + '\n').encode('utf-8'))
            await writer.drain()
        except (ConnectionError, ValueError, asyncio.IncompleteReadError):
            pass  # 用戶端斷線或請求超過上限
        finally:
            writer.close()
    return client


async def serve(path: Path, host: turn_host.TurnHost, stopping: asyncio.Event) -> None:
    prepare_socket(path)
    previous = os.umask(0o177)  # socket 檔建立時就是 0600
    try:
        server = await asyncio.start_unix_server(make_client(host), path=str(path), limit=REQUEST_LIMIT)
    finally:
        os.umask(previous)
    try:
        print(f'claude_bridge 已啟動（socket：{path}）', file=sys.stderr, flush=True)
        await stopping.wait()
    finally:
        server.close()
        await server.wait_closed()
        await host.shutdown()
        path.unlink(missing_ok=True)


def build_host(binary: str, state_dir: Path, maximum: int) -> turn_host.TurnHost:
    return turn_host.TurnHost(PROVIDER, validate=make_validate(workspaces.root(state_dir)), run=make_run(binary),
                              maximum=maximum, failed=FAILED)


async def main_async() -> None:
    check_key()
    binary = find_binary()
    host = build_host(binary, config.resolve_state_dir(), turn_host.max_timeout(TIMEOUT_ENV))
    path = Path(adapters.socket_path(PROVIDER))
    stopping = asyncio.Event()
    loop = asyncio.get_running_loop()
    for selected in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(selected, stopping.set)
    await serve(path, host, stopping)


def main() -> int:
    try:
        asyncio.run(main_async())
    except (StartupError, ValueError, OSError) as exc:  # ConfigError 是 ValueError；OSError 例如 socket 路徑太長
        print(f'claude_bridge 無法啟動：{exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
