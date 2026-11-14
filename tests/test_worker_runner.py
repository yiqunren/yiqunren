"""WorkerTurnRunner 接上真的回合橋接（scripts/turn_host.TurnHost）的離線驗收。

橋接在同一個程序裡用 Unix socket 提供服務，接的是測試專用的 testbot 轉接器；
不啟動任何 CLI、不呼叫任何 AI。
"""
import asyncio
from contextlib import ExitStack
import json
import os
from pathlib import Path
import shutil
import tempfile
import threading
import time
import unittest
from unittest import mock
import uuid

from app.services import adapters, worker_turn
from app.web.config import Settings
from app.web.runner import Hooks, Interrupted, TurnInput, Unknown
from app.web.server import create_app
from app.web.worker_runner import WorkerTurnRunner
from scripts import private_cli, turn_host
from test_web_turns import add_member, read_events, read_events_until
from web_client import PairedClient


PROGRESS = {'kind': 'item', 'event': 'completed', 'item_type': 'step', 'completed': 1}


def make_testbot():
    return adapters.Adapter(code='testbot', name='Test Bot', turn_fields=frozenset({'message', 'session_id'}),
                            auth_modes=('api_key',), strengths=('測試用能力',), weaknesses=('測試用弱點',),
                            choose_when='測試用。')


def fields(turn):
    return {'message': turn.message, 'session_id': ''}


def new_runner():
    return WorkerTurnRunner('testbot', fields=fields)


def new_turn(message='hello'):
    return TurnInput(str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4()), message, 900,
                     adapter='testbot', auth_mode='api_key')


class Bot:
    """橋接的 run 回呼：送一個進度，等 release 後回覆。stop_confirmed=False 時模擬停止未確認。"""

    def __init__(self):
        self.release = asyncio.Event()
        self.stop_confirmed, self.failure, self.content = True, None, None

    async def __call__(self, fields, progress, guard):
        progress(dict(PROGRESS))
        try:
            await self.release.wait()
        except asyncio.CancelledError:
            if not self.stop_confirmed:
                raise RuntimeError(private_cli.STOP_UNCONFIRMED) from None
            raise
        if self.failure:
            raise RuntimeError(self.failure)
        return {'content': self.content if self.content is not None else 'reply:' + fields['message']}


class Bridge:
    """一行 JSON 請求、一行 JSON 回覆的 Unix socket 伺服器，前面接 TurnHost。"""

    def __init__(self, path, bot):
        self.path, self.bot = path, bot
        self.host = turn_host.TurnHost('testbot', validate=lambda fields, auth_mode: fields, run=bot)
        self.actions, self.begin_gate, self.server, self.closed = [], None, None, False

    async def start(self):
        self.server = await asyncio.start_unix_server(self._client, path=self.path)
        return self

    async def _client(self, reader, writer):
        try:
            packet = json.loads(await reader.readline())
            self.actions.append(packet.get('action'))
            if packet.get('action') == 'turn_begin' and self.begin_gate is not None:
                await self.begin_gate.wait()
            try:
                reply = await self.host.handle(packet)
            except Exception:
                reply = {'ok': False, 'error': 'rejected'}
            writer.write((json.dumps(reply, ensure_ascii=False) + '\n').encode())
            await writer.drain()
        except ConnectionError:
            pass  # 用戶端已斷線（例如 App 關閉時取消了查詢）
        finally:
            writer.close()

    def only_call(self):
        calls = list(self.host.calls.values())
        assert len(calls) == 1, len(calls)
        return calls[0]

    async def close(self):
        if self.closed:
            return
        self.closed = True
        self.server.close()
        await self.server.wait_closed()
        await self.host.shutdown()


class Recorder:
    def __init__(self, fail_began=False, fail_save=False, on_save=None):
        self.records, self.progress, self.replies, self.sessions = [], [], [], []
        self.fail_began, self.fail_save, self.on_save = fail_began, fail_save, on_save

    def began(self, record):
        if self.fail_began:
            raise OSError('disk full')
        self.records.append(record)

    def save(self, reply, session=None):
        if self.on_save is not None:
            self.on_save()
        if self.fail_save:
            raise OSError('disk full')
        self.replies.append(reply)
        self.sessions.append(session)

    def hooks(self):
        return Hooks(self.began, self.progress.append, self.save)


async def until(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > deadline:
            raise AssertionError('等待逾時')
        await asyncio.sleep(0.005)


class BridgeEnvironment:
    """testbot 轉接器、指向臨時 socket 的環境變數、縮短查回間隔。"""

    def setUp(self):
        directory = tempfile.mkdtemp(prefix='yq-')
        self.addCleanup(shutil.rmtree, directory, True)
        self.directory = Path(directory)
        self.socket = str(self.directory / 'bridge.sock')
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(adapters.override((*adapters.adapters(), make_testbot())))
        stack.enter_context(mock.patch.dict(os.environ, {'YIQUNREN_TESTBOT_SOCKET': self.socket}))
        stack.enter_context(mock.patch.object(worker_turn, 'POLL_SECONDS', 0.01))


class WorkerRunnerTest(BridgeEnvironment, unittest.TestCase):
    def scenario(self, body):
        async def main():
            bridge = await Bridge(self.socket, Bot()).start()
            try:
                await asyncio.wait_for(body(bridge), 20)  # 退化時失敗，不要卡住整個測試
            finally:
                await bridge.close()
        asyncio.run(main())

    def test_completed_turn_is_saved_before_ack(self):
        async def body(bridge):
            acked_at_save = []
            recorder = Recorder(on_save=lambda: acked_at_save.append(bridge.only_call()['acked']))
            turn = new_turn()
            task = asyncio.create_task(new_runner().run(turn, recorder.hooks()))
            await until(lambda: recorder.progress)
            bridge.bot.release.set()
            await task
            call = bridge.only_call()
            self.assertEqual(recorder.replies, ['reply:hello'])
            self.assertEqual(recorder.progress, [PROGRESS])
            self.assertEqual(acked_at_save, [False])  # 存回覆時橋接還保留回覆
            self.assertEqual((call['state'], call['acked'], call['result']), ('done', True, None))
            record = recorder.records[0]
            self.assertEqual(len(recorder.records), 1)
            self.assertEqual((record['provider'], record['request_id'], record['epoch'], record['timeout']),
                             ('testbot', call['request_id'], bridge.host.epoch, 900))
            self.assertEqual(set(record), {'provider', 'request_id', 'call_hash', 'epoch', 'timeout', 'started_at'})
            self.assertNotIn('hello', json.dumps(record))  # 身分不含訊息內容
        self.scenario(body)

    def test_failed_save_is_not_acked_so_the_reply_stays_on_the_bridge(self):
        async def body(bridge):
            recorder = Recorder(fail_save=True)
            bridge.bot.release.set()
            with self.assertRaises(OSError):
                await new_runner().run(new_turn(), recorder.hooks())
            call = bridge.only_call()
            self.assertEqual((call['state'], call['acked']), ('done', False))
            self.assertEqual(call['result'], {'content': 'reply:hello'})
            self.assertNotIn('turn_ack', bridge.actions)
        self.scenario(body)

    def test_confirmed_stop_is_interrupted(self):
        async def body(bridge):
            recorder, runner, turn = Recorder(), new_runner(), new_turn()
            task = asyncio.create_task(runner.run(turn, recorder.hooks()))
            await until(lambda: recorder.progress)
            await runner.stop(turn.turn_id)
            with self.assertRaises(Interrupted):
                await task
            self.assertEqual(bridge.only_call()['state'], 'stopped')
            self.assertEqual(recorder.replies, [])
        self.scenario(body)

    def test_unconfirmed_stop_is_unknown(self):
        async def body(bridge):
            bridge.bot.stop_confirmed = False
            recorder, runner, turn = Recorder(), new_runner(), new_turn()
            task = asyncio.create_task(runner.run(turn, recorder.hooks()))
            await until(lambda: recorder.progress)
            await runner.stop(turn.turn_id)
            with self.assertRaises(Unknown) as caught:
                await task
            self.assertEqual(caught.exception.reason, 'stop_unconfirmed')
            self.assertEqual(bridge.only_call()['state'], 'unknown')
        self.scenario(body)

    def test_stop_before_run_starts_sends_nothing_to_the_bridge(self):
        async def body(bridge):
            recorder, runner, turn = Recorder(), new_runner(), new_turn()
            await runner.stop(turn.turn_id)
            with self.assertRaises(Interrupted):
                await runner.run(turn, recorder.hooks())
            self.assertEqual((bridge.actions, bridge.host.calls, recorder.records), ([], {}, []))
        self.scenario(body)

    def test_stop_while_begin_is_in_flight_is_sent_after_identity_is_saved(self):
        async def body(bridge):
            bridge.begin_gate = asyncio.Event()
            recorder, runner, turn = Recorder(), new_runner(), new_turn()
            task = asyncio.create_task(runner.run(turn, recorder.hooks()))
            await until(lambda: bridge.actions == ['turn_begin'])
            await runner.stop(turn.turn_id)  # 還沒拿到橋接身分：先記下
            self.assertEqual(bridge.actions, ['turn_begin'])
            bridge.begin_gate.set()
            with self.assertRaises(Interrupted):
                await task
            self.assertEqual(len(recorder.records), 1)
            self.assertEqual(bridge.actions[:2], ['turn_begin', 'turn_stop'])
            self.assertEqual(bridge.only_call()['state'], 'stopped')
        self.scenario(body)

    def test_identity_save_failure_stops_the_bridge_turn_and_is_unknown(self):
        async def body(bridge):
            with self.assertRaises(Unknown) as caught:
                await new_runner().run(new_turn(), Recorder(fail_began=True).hooks())
            self.assertEqual(caught.exception.reason, 'record_failed')
            await until(lambda: bridge.only_call()['state'] == 'stopped')
        self.scenario(body)

    def test_bridge_failure_is_a_plain_failure(self):
        async def body(bridge):
            bridge.bot.failure = 'boom'
            bridge.bot.release.set()
            recorder = Recorder()
            with self.assertRaises(RuntimeError) as caught:
                await new_runner().run(new_turn(), recorder.hooks())
            self.assertNotIsInstance(caught.exception, (worker_turn.TurnUnknown, worker_turn.TurnInterrupted))
            self.assertEqual((bridge.only_call()['state'], recorder.replies), ('failed', []))
        self.scenario(body)

    def test_bridge_not_running_fails_before_anything_starts(self):
        recorder = Recorder()
        with self.assertRaises(RuntimeError) as caught:
            asyncio.run(new_runner().run(new_turn(), recorder.hooks()))
        self.assertNotIsInstance(caught.exception, (worker_turn.TurnUnknown, worker_turn.TurnInterrupted))
        self.assertEqual(recorder.records, [])

    def test_unregistered_provider_is_refused(self):
        with self.assertRaises(ValueError):
            WorkerTurnRunner('nobody', fields=fields)

    async def start_and_shut_down(self, bridge):
        """第一個伺服器：回合被橋接接受、存下身分後，伺服器關閉（取消工作）。"""
        recorder, turn = Recorder(), new_turn()
        task = asyncio.create_task(new_runner().run(turn, recorder.hooks()))
        await until(lambda: recorder.records and recorder.progress)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        await asyncio.sleep(0.05)
        self.assertEqual(bridge.only_call()['state'], 'running')  # 關閉時不停止橋接上的回合
        self.assertNotIn('turn_stop', bridge.actions)
        return turn, json.loads(json.dumps(recorder.records[0]))  # 跟存進資料庫再讀回來一樣

    def test_resume_after_server_restart_saves_and_acks(self):
        async def body(bridge):
            turn, record = await self.start_and_shut_down(bridge)
            recorder = Recorder()
            task = asyncio.create_task(new_runner().resume(turn.turn_id, record, recorder.hooks()))
            await until(lambda: recorder.progress)  # 接回後從頭查回進度（已知會重記一次）
            bridge.bot.release.set()
            await task
            self.assertEqual(recorder.replies, ['reply:hello'])
            self.assertEqual((bridge.only_call()['acked'], bridge.only_call()['result']), (True, None))
        self.scenario(body)

    def test_stop_before_resume_is_sent_when_resume_starts(self):
        async def body(bridge):
            turn, record = await self.start_and_shut_down(bridge)
            runner = new_runner()
            await runner.stop(turn.turn_id)
            with self.assertRaises(Interrupted):
                await runner.resume(turn.turn_id, record, Recorder().hooks())
            self.assertEqual(bridge.only_call()['state'], 'stopped')
        self.scenario(body)

    def test_resume_after_bridge_restart_is_unknown(self):
        async def body(bridge):
            turn, record = await self.start_and_shut_down(bridge)
            await bridge.close()
            restarted = await Bridge(self.socket, Bot()).start()  # 新的 epoch
            try:
                with self.assertRaises(Unknown) as caught:
                    await new_runner().resume(turn.turn_id, record, Recorder().hooks())
            finally:
                await restarted.close()
            self.assertEqual(caught.exception.reason, 'bridge_restarted')
        self.scenario(body)

    def test_invalid_record_is_unknown(self):
        valid = {'provider': 'testbot', 'request_id': str(uuid.uuid4()), 'call_hash': '0' * 64,
                 'epoch': str(uuid.uuid4()), 'timeout': 900, 'started_at': 1.0}
        for record in ({}, [], {**valid, 'provider': 'nobody'}, {**valid, 'timeout': 5},
                       {**valid, 'request_id': 'x'}, {**valid, 'started_at': 'later'}):
            with self.subTest(record=record):
                with self.assertRaises(Unknown) as caught:
                    asyncio.run(new_runner().resume('t1', record, Recorder().hooks()))
                self.assertEqual(caught.exception.reason, 'record_invalid')


class BridgeThread:
    """在另一個執行緒的事件迴圈跑橋接，讓 TestClient 裡的 app 可以連過來。"""

    def __init__(self, path):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()
        self.bridge = self.call(Bridge(path, Bot()).start())

    def call(self, coroutine):
        return asyncio.run_coroutine_threadsafe(coroutine, self.loop).result(10)

    def release(self):
        self.loop.call_soon_threadsafe(self.bridge.bot.release.set)

    def calls(self):
        async def snapshot():
            return [dict(call, task=None) for call in self.bridge.host.calls.values()]
        return self.call(snapshot())

    def close(self):
        self.call(self.bridge.close())
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(10)
        self.loop.close()


def wait_for(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > deadline:
            raise AssertionError('等待逾時')
        time.sleep(0.01)


class HttpThroughBridgeTest(BridgeEnvironment, unittest.TestCase):
    """HTTP → TurnService → WorkerTurnRunner → socket → TurnHost，含伺服器重啟後接回。"""

    def setUp(self):
        super().setUp()
        self.settings = Settings(host='127.0.0.1', port=8420, state_dir=self.directory / 'state')
        self.member = add_member(self.settings.state_dir, adapter='testbot', auth_mode='api_key')
        self.bridge = BridgeThread(self.socket)
        self.addCleanup(self.bridge.close)

    def app(self):
        # 依成員的轉接器選執行者（FR-1）：testbot 的成員交給接到橋接的 WorkerTurnRunner。
        return PairedClient(create_app(self.settings, runner={'testbot': new_runner()}))

    def body(self):
        return {'request_id': str(uuid.uuid4()), 'conversation_id': str(uuid.uuid4()), 'member': self.member,
                'text': 'hello'}

    def test_turn_survives_server_restart_and_completes(self):
        body = self.body()
        with self.app() as first:
            self.assertEqual(first.post('/api/turns', json=body).status_code, 202)
            self.assertEqual(read_events_until(first, body['request_id'], 1)[0]['event'], 'progress')
        [call] = self.bridge.calls()
        self.assertEqual(call['state'], 'running')
        with self.app() as second:
            self.bridge.release()
            events = read_events(second, body['request_id'])
            self.assertEqual(events[-1]['data'], {'state': 'completed', 'error_kind': None, 'reply': 'reply:hello',
                                                 'thinking_seconds': None})
            wait_for(lambda: self.bridge.calls()[0]['acked'])
            self.assertEqual(self.bridge.calls()[0]['result'], None)

    def test_reply_over_limit_through_bridge_fails_and_is_acked(self):
        # 100,001 位元組：超過 FR-2 上限，但還在 socket 單行上限（cli_socket.MAX_RESPONSE）以內。
        self.bridge.bridge.bot.content = 'x' * 100_001
        self.bridge.release()
        body = self.body()
        with self.app() as client:
            client.post('/api/turns', json=body)
            events = read_events(client, body['request_id'])
            self.assertEqual(events[-1]['data'], {'state': 'failed', 'error_kind': 'reply_too_long', 'reply': None,
                                                 'thinking_seconds': None})
            wait_for(lambda: self.bridge.calls()[0]['acked'])  # 結果已寫進資料庫，橋接可以丟掉回覆

    def test_interrupt_through_bridge(self):
        body = self.body()
        with self.app() as client:
            client.post('/api/turns', json=body)
            read_events_until(client, body['request_id'], 1)
            self.assertEqual(client.post('/api/turns/%s/interrupt' % body['request_id']).status_code, 202)
            events = read_events(client, body['request_id'])
            self.assertEqual([e['event'] for e in events][-2:], ['stopping', 'done'])
            self.assertEqual(events[-1]['data']['state'], 'interrupted')
        self.assertEqual(self.bridge.calls()[0]['state'], 'stopped')


if __name__ == '__main__':
    unittest.main()
