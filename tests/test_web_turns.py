"""FR-2 私聊回合 HTTP／SSE 介面的離線驗收；只用假轉接器與臨時目錄，不呼叫任何 AI。"""
import asyncio
import json
from pathlib import Path
import tempfile
import unittest
import uuid

from fastapi.testclient import TestClient

from app.web.config import Settings
from app.web.fake_runner import FakeRunner
from app.web.server import create_app
from app.web.turns import MAX_MESSAGE_CHARS


def read_events(client, turn_id, last_event_id=None):
    headers = {'Last-Event-ID': last_event_id} if last_event_id else {}
    events, current = [], {}
    with client.stream('GET', '/api/turns/%s/events' % turn_id, headers=headers) as response:
        assert response.status_code == 200, response.status_code
        for line in response.iter_lines():
            if line.startswith(':'):
                continue
            if not line:
                if current:
                    events.append(current)
                    if current.get('event') == 'done':
                        break
                current = {}
                continue
            key, _, value = line.partition(': ')
            current[key] = json.loads(value) if key == 'data' else value
    return events


class FailingRunner:
    async def __call__(self, member, text, emit):
        await emit({'step': 1})
        raise RuntimeError('raw provider error with sensitive detail')


class BlockingRunner:
    """一直不結束，直到伺服器關閉把它取消。"""
    async def __call__(self, member, text, emit):
        await emit({'step': 1})
        await asyncio.sleep(3600)


class TurnApiTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='yiqunren-web-turns-test-')
        self.addCleanup(self.temporary.cleanup)
        self.settings = Settings(host='127.0.0.1', port=8420, state_dir=Path(self.temporary.name) / 'state')

    def client(self, runner=None, settings=None, **options):
        client = TestClient(create_app(settings or self.settings,
                                       runner=runner if runner is not None else FakeRunner(steps=3, tick=0.02),
                                       **options))
        client.__enter__()
        self.addCleanup(client.__exit__, None, None, None)
        return client

    def body(self, **changes):
        return {'request_id': str(uuid.uuid4()), 'conversation_id': str(uuid.uuid4()),
                'member': 'm1', 'text': 'hello', **changes}

    def test_turn_runs_to_completion_and_streams_ordered_events(self):
        client = self.client()
        body = self.body()
        response = client.post('/api/turns', json=body)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()['turn']['state'], 'running')
        events = read_events(client, body['request_id'])
        self.assertEqual([e['id'] for e in events], ['1', '2', '3', '4'])
        self.assertEqual([e['event'] for e in events], ['progress'] * 3 + ['done'])
        done = events[-1]['data']
        self.assertEqual((done['state'], done['error_kind']), ('completed', None))
        self.assertTrue(done['reply'])
        turn = client.get('/api/turns/' + body['request_id']).json()['turn']
        self.assertEqual((turn['state'], turn['reply']), ('completed', done['reply']))
        self.assertIsNotNone(turn['finished'])

    def test_refresh_replays_everything_and_reconnect_resumes_after_last_event_id(self):
        client = self.client()
        body = self.body()
        client.post('/api/turns', json=body)
        first = read_events(client, body['request_id'])
        self.assertEqual(read_events(client, body['request_id']), first)  # 重新整理：完整重送
        resumed = read_events(client, body['request_id'], last_event_id='2')  # 自動重連：只補送之後的
        self.assertEqual([e['id'] for e in resumed], ['3', '4'])
        self.assertEqual(read_events(client, body['request_id'], last_event_id='junk'), first)

    def test_resend_is_idempotent_and_changed_content_is_rejected(self):
        client = self.client()
        body = self.body()
        self.assertEqual(client.post('/api/turns', json=body).status_code, 202)
        again = client.post('/api/turns', json=body)
        self.assertEqual(again.status_code, 200)
        self.assertEqual(again.json()['turn']['id'], body['request_id'])
        self.assertEqual(client.post('/api/turns', json={**body, 'text': 'changed'}).status_code, 409)
        read_events(client, body['request_id'])
        # 結束後重送同一個請求，回傳原本的結果，不再執行一次。
        final = client.post('/api/turns', json=body)
        self.assertEqual((final.status_code, final.json()['turn']['state']), (200, 'completed'))
        self.assertEqual(len(read_events(client, body['request_id'])), 4)

    def test_one_running_turn_per_conversation(self):
        client = self.client(runner=FakeRunner(steps=3, tick=0.2))
        first = self.body()
        self.assertEqual(client.post('/api/turns', json=first).status_code, 202)
        blocked = self.body(conversation_id=first['conversation_id'])
        response = client.post('/api/turns', json=blocked)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(client.get('/api/turns/' + blocked['request_id']).status_code, 404)
        self.assertEqual(client.post('/api/turns', json=self.body()).status_code, 202)  # 其他對話照常
        read_events(client, first['request_id'])
        # 上一個回合結束後，被擋下的同一個請求可以重送成功。
        self.assertEqual(client.post('/api/turns', json=blocked).status_code, 202)

    def test_failure_shows_fixed_category_without_raw_error(self):
        client = self.client(runner=FailingRunner())
        body = self.body()
        client.post('/api/turns', json=body)
        events = read_events(client, body['request_id'])
        self.assertEqual(events[-1]['data'], {'state': 'failed', 'error_kind': 'internal_error', 'reply': None})
        everything = json.dumps(events) + client.get('/api/turns/' + body['request_id']).text
        self.assertNotIn('sensitive', everything)

    def test_server_restart_marks_running_turn_unknown(self):
        body = self.body()
        first = TestClient(create_app(self.settings, runner=BlockingRunner()))
        with first:
            self.assertEqual(first.post('/api/turns', json=body).status_code, 202)
            self.assertEqual(read_events_until(first, body['request_id'], 1)[0]['event'], 'progress')
        client = self.client()
        turn = client.get('/api/turns/' + body['request_id']).json()['turn']
        self.assertEqual(turn['state'], 'unknown')
        events = read_events(client, body['request_id'])
        self.assertEqual(events[-1]['data']['state'], 'unknown')

    def test_conversation_shows_messages_and_replies_after_restart(self):
        body = self.body(text='第一個問題')
        with TestClient(create_app(self.settings, runner=FakeRunner(steps=1, tick=0.01))) as first:
            first.post('/api/turns', json=body)
            read_events(first, body['request_id'])
            second = self.body(conversation_id=body['conversation_id'], text='第二個問題')
            first.post('/api/turns', json=second)
            read_events(first, second['request_id'])
        client = self.client()  # 伺服器重啟後
        response = client.get('/api/conversations/' + body['conversation_id'])
        self.assertEqual(response.status_code, 200)
        listed = response.json()['turns']
        self.assertEqual([t['message'] for t in listed], ['第一個問題', '第二個問題'])
        self.assertTrue(all(t['state'] == 'completed' and t['reply'] for t in listed))
        self.assertEqual(client.get('/api/turns/' + body['request_id']).json()['turn']['message'], '第一個問題')

    def test_delete_conversation(self):
        client = self.client(runner=FakeRunner(steps=2, tick=0.2))
        body = self.body()
        client.post('/api/turns', json=body)
        # 進行中不能刪
        self.assertEqual(client.delete('/api/conversations/' + body['conversation_id']).status_code, 409)
        read_events(client, body['request_id'])
        other = self.body()
        client.post('/api/turns', json=other)
        read_events(client, other['request_id'])
        self.assertEqual(client.delete('/api/conversations/' + body['conversation_id']).status_code, 204)
        self.assertEqual(client.get('/api/conversations/' + body['conversation_id']).status_code, 404)
        self.assertEqual(client.get('/api/turns/' + body['request_id']).status_code, 404)
        self.assertEqual(client.get('/api/turns/%s/events' % body['request_id']).status_code, 404)
        self.assertEqual(client.get('/api/conversations/' + other['conversation_id']).status_code, 200)
        # 刪除後用同一個請求重送：明確告知已刪除，不重新執行
        self.assertEqual(client.post('/api/turns', json=body).status_code, 410)
        self.assertEqual(client.get('/api/conversations/' + body['conversation_id']).status_code, 404)
        # 同一段對話之後可以用新的請求重新開始
        self.assertEqual(client.post('/api/turns', json={**body, 'request_id': str(uuid.uuid4())}).status_code, 202)
        self.assertEqual(client.delete('/api/conversations/' + str(uuid.uuid4())).status_code, 404)
        self.assertEqual(client.delete('/api/conversations/not-a-uuid').status_code, 422)
        self.assertEqual(client.get('/api/conversations/not-a-uuid').status_code, 422)

    def test_interrupt_marks_interrupted_after_runner_confirms_stop(self):
        client = self.client(runner=FakeRunner(steps=200, tick=0.05))
        body = self.body()
        client.post('/api/turns', json=body)
        self.assertEqual(read_events_until(client, body['request_id'], 1)[0]['event'], 'progress')
        response = client.post('/api/turns/%s/interrupt' % body['request_id'])
        self.assertEqual(response.status_code, 202)
        events = read_events(client, body['request_id'])
        self.assertEqual(events[-1]['data'], {'state': 'interrupted', 'error_kind': None, 'reply': None})
        self.assertEqual(client.get('/api/turns/' + body['request_id']).json()['turn']['state'], 'interrupted')
        again = client.post('/api/turns/%s/interrupt' % body['request_id'])
        self.assertEqual((again.status_code, again.json()['turn']['state']), (409, 'interrupted'))
        # 重送同一個請求回傳原結果，不重新執行；同一段對話可以開新回合。
        resent = client.post('/api/turns', json=body)
        self.assertEqual((resent.status_code, resent.json()['turn']['state']), (200, 'interrupted'))
        self.assertEqual(client.post('/api/turns', json={**body, 'request_id': str(uuid.uuid4())}).status_code, 202)

    def test_interrupt_without_confirmed_stop_is_unknown(self):
        client = self.client(runner=FakeRunner(steps=200, tick=0.05, stop_confirmed=False))
        body = self.body()
        client.post('/api/turns', json=body)
        read_events_until(client, body['request_id'], 1)
        self.assertEqual(client.post('/api/turns/%s/interrupt' % body['request_id']).status_code, 202)
        self.assertEqual(read_events(client, body['request_id'])[-1]['data']['state'], 'unknown')

    def test_interrupt_finished_or_missing_turn(self):
        client = self.client()
        body = self.body()
        client.post('/api/turns', json=body)
        read_events(client, body['request_id'])
        response = client.post('/api/turns/%s/interrupt' % body['request_id'])
        self.assertEqual((response.status_code, response.json()['turn']['state']), (409, 'completed'))
        self.assertEqual(client.post('/api/turns/%s/interrupt' % uuid.uuid4()).status_code, 404)

    def test_timeout_fails_with_timeout_category(self):
        client = self.client(runner=FakeRunner(steps=200, tick=0.05), turn_timeout=0.3)
        body = self.body()
        client.post('/api/turns', json=body)
        events = read_events(client, body['request_id'])
        self.assertGreaterEqual(len(events), 2)  # 逾時前有進度
        self.assertEqual(events[-1]['data'], {'state': 'failed', 'error_kind': 'timeout', 'reply': None})

    def test_timeout_without_confirmed_stop_is_unknown(self):
        client = self.client(runner=FakeRunner(steps=200, tick=0.05, stop_confirmed=False), turn_timeout=0.3)
        body = self.body()
        client.post('/api/turns', json=body)
        self.assertEqual(read_events(client, body['request_id'])[-1]['data']['state'], 'unknown')

    def test_runner_own_timeout_error_is_not_reported_as_turn_timeout(self):
        class OwnTimeout:
            async def __call__(self, member, text, emit):
                raise TimeoutError('provider socket timed out')
        client = self.client(runner=OwnTimeout())
        body = self.body()
        client.post('/api/turns', json=body)
        self.assertEqual(read_events(client, body['request_id'])[-1]['data']['error_kind'], 'internal_error')

    def test_without_runner_turns_are_refused_and_nothing_is_stored(self):
        client = TestClient(create_app(self.settings))
        with client:
            body = self.body()
            self.assertEqual(client.post('/api/turns', json=body).status_code, 503)
            self.assertEqual(client.get('/api/turns/' + body['request_id']).status_code, 404)

    def test_fake_turns_setting_enables_fake_runner(self):
        client = TestClient(create_app(Settings('127.0.0.1', 8420, self.settings.state_dir, fake_turns=True)))
        with client:
            self.assertEqual(client.post('/api/turns', json=self.body()).status_code, 202)

    def test_invalid_requests_are_rejected(self):
        client = self.client()
        for changes in ({'request_id': 'not-a-uuid'}, {'conversation_id': 'x'}, {'member': ''},
                        {'text': ''}, {'text': 'a' * (MAX_MESSAGE_CHARS + 1)}, {'extra': 1}):
            with self.subTest(changes=list(changes)):
                self.assertEqual(client.post('/api/turns', json=self.body(**changes)).status_code, 422)
        self.assertEqual(client.get('/api/turns/' + str(uuid.uuid4())).status_code, 404)
        self.assertEqual(client.get('/api/turns/%s/events' % uuid.uuid4()).status_code, 404)


class InterruptBeforeStartTest(unittest.TestCase):
    """中斷在回合工作開始執行前就送到：執行者不會被呼叫，回合直接標為已中斷。"""

    def test_interrupt_before_runner_starts(self):
        from app.storage import db
        from app.web.turns import TurnRequest, TurnService

        with tempfile.TemporaryDirectory(prefix='yiqunren-interrupt-test-') as temporary:
            path = db.prepare(Path(temporary) / 'state')
            called = []

            async def runner(member, text, emit):
                called.append(True)
                return 'should not run'

            async def scenario():
                service = TurnService(path, runner)
                body = TurnRequest(request_id=str(uuid.uuid4()), conversation_id=str(uuid.uuid4()),
                                   member='m1', text='hi')
                self.assertEqual(service.start(body)[0], 202)
                self.assertEqual(service.interrupt(body.request_id)[0], 202)  # 同步呼叫，中間沒有讓工作開始
                await asyncio.sleep(0.05)
                return service.get(body.request_id)['state'], service.events_after(body.request_id, 0)

            state, events = asyncio.run(scenario())
        self.assertEqual(called, [])
        self.assertEqual(state, 'interrupted')
        self.assertEqual(events, [(1, 'done', {'state': 'interrupted', 'error_kind': None})])


def read_events_until(client, turn_id, count):
    events, current = [], {}
    with client.stream('GET', '/api/turns/%s/events' % turn_id) as response:
        for line in response.iter_lines():
            if line.startswith(':'):
                continue
            if not line:
                if current:
                    events.append(current)
                    if len(events) >= count:
                        break
                current = {}
                continue
            key, _, value = line.partition(': ')
            current[key] = value
    return events


if __name__ == '__main__':
    unittest.main()
