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

    def client(self, runner=None, settings=None):
        client = TestClient(create_app(settings or self.settings,
                                       runner=runner if runner is not None else FakeRunner(steps=3, tick=0.02)))
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
