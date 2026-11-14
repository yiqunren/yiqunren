"""Claude Code 橋接（scripts/claude_bridge.py）的離線驗收。

用一個假的 claude 執行檔代替真的 CLI：記下收到的參數、工作目錄與 stdin，再依 FAKE_CLAUDE_MODE 輸出 stream-json。
不呼叫任何 AI、不需要真的 API key（環境變數只放測試用的假值）。
"""
import asyncio
from contextlib import ExitStack, redirect_stderr
import io
import json
import os
from pathlib import Path
import shutil
import socket
import stat
import sys
import tempfile
import unittest
from unittest import mock
import uuid

from app.services import turn_contract as contract
from app.services import worker_turn
from app.storage import workspaces
from app.web import bridges
from app.web.config import ConfigError
from app.web.runner import Hooks, TurnInput
from scripts import claude_bridge


SESSION = '0b7c4f9e-2d1a-4c3b-9e8f-1a2b3c4d5e6f'
FAKE = r'''
import json, os, sys, time
record = {'argv': sys.argv[1:], 'cwd': os.getcwd(), 'stdin': sys.stdin.read(),
          'has_key': bool(os.environ.get('ANTHROPIC_API_KEY'))}
with open(os.environ['FAKE_CLAUDE_RECORD'], 'a') as stream:
    stream.write(json.dumps(record) + '\n')
mode = os.environ.get('FAKE_CLAUDE_MODE', 'success')
session = os.environ.get('FAKE_CLAUDE_SESSION', '%s')

def emit(event):
    print(json.dumps(event), flush=True)

emit({'type': 'system', 'subtype': 'init', 'session_id': session})
if mode == 'sleep':
    time.sleep(60)
emit({'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': 'working'},
                                                   {'type': 'tool_use', 'id': 't1', 'name': 'Edit', 'input': {}}]}})
reply = 'reply:' + record['stdin']
if mode == 'big':
    reply = 'x' * 120000
if mode in ('success', 'big', 'exit1'):
    emit({'type': 'result', 'subtype': 'success', 'is_error': False, 'result': reply, 'session_id': session,
          'total_cost_usd': 0.01})
elif mode == 'error_result':
    emit({'type': 'result', 'subtype': 'error_max_budget_usd', 'is_error': True, 'session_id': session})
elif mode == 'is_error':
    emit({'type': 'result', 'subtype': 'success', 'is_error': True, 'result': 'API Error', 'session_id': session})
sys.exit(1 if mode in ('exit1', 'error_result') else 0)
''' % SESSION


class BridgeEnvironment(unittest.TestCase):
    def setUp(self):
        directory = Path(tempfile.mkdtemp(prefix='yq-cb-'))
        self.addCleanup(shutil.rmtree, directory, True)
        self.state = directory / 'state'
        self.state.mkdir(mode=0o700)
        self.records = directory / 'records.jsonl'
        self.diag = directory / 'diag'
        self.socket = directory / 'run' / 'claude.sock'
        bin_dir = directory / 'bin'
        bin_dir.mkdir()
        fake = bin_dir / 'claude'
        fake.write_text('#!' + sys.executable + '\n' + FAKE, encoding='utf-8')
        fake.chmod(0o755)
        self.binary = str(fake)
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(mock.patch.dict(os.environ, {
            'ANTHROPIC_API_KEY': 'test-placeholder', 'FAKE_CLAUDE_RECORD': str(self.records),
            'FAKE_CLAUDE_MODE': 'success', 'YIQUNREN_WRITE_REGISTRY': str(directory / 'registry.sqlite3'),
            'YIQUNREN_DIAG_DIR': str(self.diag), 'YIQUNREN_STATE_DIR': str(self.state),
            'YIQUNREN_CLAUDE_CODE_SOCKET': str(self.socket)}))
        stack.enter_context(mock.patch.object(worker_turn, 'POLL_SECONDS', 0.01))
        self.root = workspaces.root(self.state)
        self.workspace = workspaces.ensure(str(workspaces.path(self.state, str(uuid.uuid4()))), self.root)

    def mode(self, value):
        patcher = mock.patch.dict(os.environ, {'FAKE_CLAUDE_MODE': value})
        patcher.start()
        self.addCleanup(patcher.stop)

    def calls(self):
        if not self.records.exists():
            return []
        return [json.loads(line) for line in self.records.read_text(encoding='utf-8').splitlines()]

    def fields(self, **changes):
        values = {'message': 'hello', 'session_id': None, 'workspace': str(self.workspace), 'model': None,
                  'effort': None, 'max_budget_usd': None}
        values.update(changes)
        return values

    def turn(self, *, stop=False, **changes):
        """直接對 TurnHost 送 turn_begin，查回到結束；stop=True 時等 CLI 啟動後送 turn_stop。回傳（turn, 進度項）。"""
        async def main():
            host = claude_bridge.build_host(self.binary, self.state, contract.TIMEOUT_MAX)
            begin = contract.begin_packet('claude_code', str(uuid.uuid4()), self.fields(**changes), 60,
                                          auth_mode='api_key')
            try:
                epoch = (await host.handle(begin))['epoch']
                stopped = False
                while True:
                    if stop and not stopped and self.calls():
                        await host.handle(contract.control_packet('turn_stop', begin, epoch))
                        stopped = True
                    turn = (await host.handle(contract.control_packet('turn_status', begin, epoch)))['turn']
                    if turn['state'] in contract.TERMINAL:
                        progress = [entry['item'] for entry in host.calls[begin['request_id']]['progress']]
                        return turn, progress
                    await asyncio.sleep(0.02)
            finally:
                await host.shutdown()
        return asyncio.run(asyncio.wait_for(main(), 30))

    def diag_files(self):
        directory = self.diag / 'claude_code'
        return sorted(directory.glob('*.log')) if directory.exists() else []


class CommandTest(BridgeEnvironment):
    def test_isolation_and_permission_flags(self):
        turn, progress = self.turn()
        self.assertEqual(turn['state'], 'done')
        self.assertEqual(turn['result'], {'content': 'reply:hello', 'session': SESSION})
        self.assertEqual(progress, [{'kind': 'item', 'event': 'started', 'item_type': 'Edit'}])
        [call] = self.calls()
        argv = call['argv']
        self.assertEqual(argv[:12], ['--bare', '-p', '--output-format', 'stream-json', '--verbose',
                                     '--permission-mode', 'acceptEdits', '--disallowedTools', 'Bash', 'Monitor',
                                     'PowerShell', '--settings'])
        settings = json.loads(argv[argv.index('--settings') + 1])
        self.assertEqual(settings, {'permissions': {'blockReadsOutsideWorkingDirectories': True,
                                                    'blockWritesOutsideWorkingDirectories': True}})
        for flag in ('--resume', '--model', '--effort', '--max-budget-usd'):
            self.assertNotIn(flag, argv)
        self.assertNotIn('hello', argv)  # 訊息只走 stdin
        self.assertEqual(call['stdin'], 'hello')
        self.assertEqual(call['cwd'], str(self.workspace))
        self.assertTrue(call['has_key'])

    def test_optional_flags_and_resume(self):
        turn, _ = self.turn(session_id=SESSION, model='claude-sonnet-5-5', effort='high', max_budget_usd=2.5)
        self.assertEqual(turn['state'], 'done')
        argv = self.calls()[0]['argv']
        self.assertEqual(argv[argv.index('--resume') + 1], SESSION)
        self.assertEqual(argv[argv.index('--model') + 1], 'claude-sonnet-5-5')
        self.assertEqual(argv[argv.index('--effort') + 1], 'high')
        self.assertEqual(argv[argv.index('--max-budget-usd') + 1], '2.5')

    def test_reply_session_must_be_uuid(self):
        with mock.patch.dict(os.environ, {'FAKE_CLAUDE_SESSION': '../not-a-session'}):
            turn, _ = self.turn()
        self.assertEqual(turn['result'], {'content': 'reply:hello', 'session': None})


class ValidateTest(BridgeEnvironment):
    def validate(self, auth_mode='api_key', **changes):
        return claude_bridge.make_validate(self.root)(self.fields(**changes), auth_mode)

    def test_accepts_valid_fields(self):
        self.assertEqual(self.validate(session_id=SESSION, model='opus[1m]', effort='max', max_budget_usd=1),
                         {'message': 'hello', 'session': SESSION, 'model': 'opus[1m]', 'effort': 'max',
                          'budget': 1, 'workspace': str(self.workspace)})

    def test_rejects_invalid_fields(self):
        outside = Path(tempfile.mkdtemp(prefix='yq-out-'))
        self.addCleanup(shutil.rmtree, outside, True)
        link = self.root / str(uuid.uuid4())
        link.symlink_to(outside)
        cases = {
            'subscription mode': {'auth_mode': 'subscription_cli'},
            'blank message': {'message': '  '},
            'session not uuid': {'session_id': '--help'},
            'model looks like a flag': {'model': '--dangerously-skip-permissions'},
            'model with space': {'model': 'opus x'},
            'unknown effort': {'effort': 'ultra'},
            'budget bool': {'max_budget_usd': True},
            'budget zero': {'max_budget_usd': 0},
            'budget too high': {'max_budget_usd': 5000},
            'workspace outside root': {'workspace': str(outside)},
            'workspace missing': {'workspace': str(self.root / str(uuid.uuid4()))},
            'workspace symlink': {'workspace': str(link)},
            'workspace not text': {'workspace': None},
        }
        for name, change in cases.items():
            with self.subTest(name):
                with self.assertRaises(ValueError):
                    self.validate(**change)

    def test_invalid_begin_does_not_start_cli(self):
        async def main():
            host = claude_bridge.build_host(self.binary, self.state, contract.TIMEOUT_MAX)
            begin = contract.begin_packet('claude_code', str(uuid.uuid4()), self.fields(model='-x'), 60,
                                          auth_mode='api_key')
            with self.assertRaises(ValueError):
                await host.handle(begin)
            self.assertEqual(host.calls, {})
        asyncio.run(main())
        self.assertEqual(self.calls(), [])


class FailureTest(BridgeEnvironment):
    def assert_failed(self, turn, reason, message=claude_bridge.FAILED):
        self.assertEqual(turn['state'], 'failed')
        self.assertTrue(turn['error'].startswith(message + '（診斷 ID：'), turn['error'])
        [path] = self.diag_files()
        text = path.read_text(encoding='utf-8')
        self.assertIn('reason: ' + reason, text)
        self.assertNotIn('reply:hello', text)  # 診斷檔不寫回覆正文
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_error_result(self):
        self.mode('error_result')
        turn, _ = self.turn()
        self.assert_failed(turn, 'exit_nonzero')
        self.assertIn('error_class:', self.diag_files()[0].read_text(encoding='utf-8'))

    def test_success_subtype_with_is_error(self):
        self.mode('is_error')
        turn, _ = self.turn()
        self.assert_failed(turn, 'parse_failed')

    def test_no_result_event(self):
        self.mode('no_result')
        turn, _ = self.turn()
        self.assert_failed(turn, 'parse_failed')

    def test_nonzero_exit_even_with_success_result(self):
        self.mode('exit1')
        turn, _ = self.turn()
        self.assert_failed(turn, 'exit_nonzero')

    def test_reply_too_large_for_bridge_line(self):
        self.mode('big')
        turn, _ = self.turn()
        self.assert_failed(turn, 'oversize', claude_bridge.REPLY_OVERSIZE)

    def test_stop_ends_process_group(self):
        self.mode('sleep')
        turn, _ = self.turn(stop=True)
        self.assertEqual(turn['state'], 'stopped')
        self.assertEqual(self.diag_files(), [])


class SocketChainTest(BridgeEnvironment):
    def test_backend_runner_through_socket_and_resume(self):
        conversation = str(uuid.uuid4())
        workspace = workspaces.path(self.state, conversation)
        saved = []

        def hooks():
            return Hooks(began=lambda record: None, progress=lambda item: None,
                         save=lambda reply, session=None: saved.append((reply, session)))

        def turn_input(message, **changes):
            return TurnInput(str(uuid.uuid4()), conversation, str(uuid.uuid4()), message, 60,
                             adapter='claude_code', auth_mode='api_key', workspace=str(workspace), **changes)

        async def main():
            host = claude_bridge.build_host(self.binary, self.state, contract.TIMEOUT_MAX)
            stopping = asyncio.Event()
            server = asyncio.create_task(claude_bridge.serve(self.socket, host, stopping))
            while not self.socket.exists():
                await asyncio.sleep(0.01)
            self.assertEqual(stat.S_IMODE(self.socket.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(self.socket.parent.stat().st_mode), 0o700)
            runner = bridges.runners(('claude_code',), self.state)['claude_code']
            await runner.run(turn_input('first'), hooks())
            await runner.run(turn_input('second', session=saved[0][1], model='claude-sonnet-5-5', effort='high'),
                             hooks())
            stopping.set()
            await server

        with redirect_stderr(io.StringIO()):
            asyncio.run(asyncio.wait_for(main(), 30))
        self.assertEqual(saved, [('reply:first', SESSION), ('reply:second', SESSION)])
        first, second = self.calls()
        self.assertEqual(first['cwd'], str(workspace))
        self.assertEqual(stat.S_IMODE(workspace.stat().st_mode), 0o700)  # 第一次送出回合時建立
        self.assertNotIn('--resume', first['argv'])
        self.assertEqual(second['argv'][second['argv'].index('--resume') + 1], SESSION)
        self.assertNotIn('--max-budget-usd', second['argv'])  # 目前不設預算上限
        self.assertFalse(self.socket.exists())  # 關閉時刪掉 socket

    def test_only_implemented_bridges(self):
        with self.assertRaises(ConfigError):
            bridges.runners(('codex',), self.state)

    def test_fields_drop_nothing_required(self):
        fields = bridges.claude_code_fields(self.state)(
            TurnInput(str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4()), 'hi', 60, adapter='claude_code',
                      auth_mode='api_key', model='', workspace=str(self.workspace)))
        self.assertEqual(fields, {'message': 'hi', 'session_id': None, 'workspace': str(self.workspace),
                                  'model': None, 'effort': None, 'max_budget_usd': None})


class SocketPrepareTest(BridgeEnvironment):
    def bound(self, listen):
        self.socket.parent.mkdir(mode=0o700)
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(self.socket))
        if listen:
            server.listen()
        else:
            server.close()
        return server

    def test_stale_socket_is_replaced(self):
        self.bound(listen=False)
        claude_bridge.prepare_socket(self.socket)
        self.assertFalse(self.socket.exists())

    def test_live_socket_refuses_start(self):
        server = self.bound(listen=True)
        self.addCleanup(server.close)
        with self.assertRaises(claude_bridge.StartupError):
            claude_bridge.prepare_socket(self.socket)
        self.assertTrue(self.socket.exists())

    def test_other_file_refuses_start(self):
        self.socket.parent.mkdir(mode=0o700)
        self.socket.write_text('x')
        with self.assertRaises(claude_bridge.StartupError):
            claude_bridge.prepare_socket(self.socket)
        self.assertTrue(self.socket.exists())

    def test_shared_directory_refuses_start(self):
        self.socket.parent.mkdir()
        self.socket.parent.chmod(0o755)
        with self.assertRaises(claude_bridge.StartupError):
            claude_bridge.prepare_socket(self.socket)


class StartupTest(BridgeEnvironment):
    def test_key_is_required(self):
        with self.assertRaises(claude_bridge.StartupError):
            claude_bridge.check_key({})
        with self.assertRaises(claude_bridge.StartupError):
            claude_bridge.check_key({'ANTHROPIC_API_KEY': ''})
        claude_bridge.check_key({'ANTHROPIC_API_KEY': 'test-placeholder'})

    def test_binary_lookup(self):
        self.assertEqual(claude_bridge.find_binary({'YIQUNREN_CLAUDE_BIN': self.binary}), self.binary)
        self.assertEqual(claude_bridge.find_binary({'PATH': str(Path(self.binary).parent)}), self.binary)
        for env in ({'YIQUNREN_CLAUDE_BIN': 'claude'}, {'YIQUNREN_CLAUDE_BIN': str(self.state / 'claude')},
                    {'PATH': str(self.state)}):
            with self.subTest(env=env):
                with self.assertRaises(claude_bridge.StartupError):
                    claude_bridge.find_binary(env)

    def test_main_refuses_without_key(self):
        environment = {key: value for key, value in os.environ.items() if key != 'ANTHROPIC_API_KEY'}
        with mock.patch.dict(os.environ, environment, clear=True), redirect_stderr(io.StringIO()) as err:
            self.assertEqual(claude_bridge.main(), 2)
        self.assertIn('ANTHROPIC_API_KEY', err.getvalue())
        self.assertFalse(self.socket.exists())


if __name__ == '__main__':
    unittest.main()
