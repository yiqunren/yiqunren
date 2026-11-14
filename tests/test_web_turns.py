"""FR-2 私聊回合 HTTP／SSE 介面的離線驗收；只用假轉接器與臨時目錄，不呼叫任何 AI。"""
import asyncio
import json
from pathlib import Path
import tempfile
import unittest
import uuid

from app.storage import db, members, requests
from app.web.config import Settings
from app.web.fake_runner import FakeRunner
from app.web.runner import Failed, Interrupted, Runner, Unknown
from app.web.server import create_app
from app.web.turns import MAX_MESSAGE_CHARS, MAX_REPLY_BYTES
from web_client import PairedClient


def add_member(state_dir, *, adapter='codex', name='成員一', auth_mode='api_key', timeout=900, enabled=True):
    """直接在狀態資料庫建立一位成員（不經 HTTP），回傳成員 ID。"""
    member_id = str(uuid.uuid4())
    connection = db.connect(db.prepare(Path(state_dir)))
    try:
        requests.claim(connection, member_id, 'member_create', {'test': member_id},
                       on_claim=lambda c, now: members.insert(c, member_id, adapter=adapter, name=name, model='',
                                                              effort=None, auth_mode=auth_mode, timeout=timeout,
                                                              now=now))
        if not enabled:
            members.update(connection, member_id, {'enabled': False}, 0.0)
    finally:
        connection.close()
    return member_id


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


class FailingRunner(Runner):
    async def run(self, turn, hooks):
        hooks.progress({'step': 1})
        raise RuntimeError('raw provider error with sensitive detail')


class BlockingRunner(Runner):
    """一直不結束，直到伺服器關閉把它取消；沒有存轉接器身分，重啟後無法接回。"""
    async def run(self, turn, hooks):
        hooks.progress({'step': 1})
        await asyncio.sleep(3600)


class RaisingRunner(Runner):
    """一開始就以指定的例外結束，或沒交出回覆就返回（error=None）。"""
    def __init__(self, error=None):
        self.error = error

    async def run(self, turn, hooks):
        if self.error is not None:
            raise self.error


class ReplyRunner(Runner):
    """直接交出指定的回覆。"""
    def __init__(self, reply):
        self.reply, self.save_raised = reply, None

    async def run(self, turn, hooks):
        try:
            hooks.save(self.reply)
        except Exception as exc:
            self.save_raised = exc


class UnreachableStopRunner(BlockingRunner):
    async def stop(self, turn_id):
        raise OSError('bridge socket gone')


class RecordingRunner(Runner):
    """存下轉接器身分後一直不結束，直到伺服器關閉；重啟後 resume 依 resume_with 決定結果：
    文字就當回覆存下，例外就丟出，None 則不支援接回。"""
    def __init__(self, resume_with=None):
        self.resume_with, self.resumed = resume_with, []

    async def run(self, turn, hooks):
        hooks.began({'bridge_turn': 'b-' + turn.turn_id, 'epoch': 'e1'})
        hooks.progress({'step': 1})
        await asyncio.sleep(3600)

    async def resume(self, turn_id, record, hooks):
        self.resumed.append((turn_id, record))
        if self.resume_with is None:
            raise NotImplementedError
        hooks.progress({'step': 2})
        if isinstance(self.resume_with, Exception):
            raise self.resume_with
        hooks.save(self.resume_with)


class TurnApiTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='yiqunren-web-turns-test-')
        self.addCleanup(self.temporary.cleanup)
        self.settings = Settings(host='127.0.0.1', port=8420, state_dir=Path(self.temporary.name) / 'state')
        self.member = add_member(self.settings.state_dir)

    def client(self, runner=None, settings=None, **options):
        client = PairedClient(create_app(settings or self.settings,
                                       runner=runner if runner is not None else FakeRunner(steps=3, tick=0.02),
                                       **options))
        client.__enter__()
        self.addCleanup(client.__exit__, None, None, None)
        return client

    def body(self, **changes):
        return {'request_id': str(uuid.uuid4()), 'conversation_id': str(uuid.uuid4()),
                'member': self.member, 'text': 'hello', **changes}

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
        first = PairedClient(create_app(self.settings, runner=BlockingRunner()))
        with first:
            self.assertEqual(first.post('/api/turns', json=body).status_code, 202)
            self.assertEqual(read_events_until(first, body['request_id'], 1)[0]['event'], 'progress')
        client = self.client()
        turn = client.get('/api/turns/' + body['request_id']).json()['turn']
        self.assertEqual(turn['state'], 'unknown')
        events = read_events(client, body['request_id'])
        self.assertEqual(events[-1]['data']['state'], 'unknown')

    def start_recorded_turn_and_shut_down(self):
        """第一次啟動：回合存下轉接器身分後伺服器關閉，回合留在進行中。"""
        body = self.body()
        with PairedClient(create_app(self.settings, runner=RecordingRunner())) as first:
            self.assertEqual(first.post('/api/turns', json=body).status_code, 202)
            self.assertEqual(read_events_until(first, body['request_id'], 1)[0]['event'], 'progress')
        return body

    def test_restart_reattaches_recorded_turn(self):
        body = self.start_recorded_turn_and_shut_down()
        runner = RecordingRunner(resume_with='接回後的回覆')
        client = self.client(runner=runner)
        events = read_events(client, body['request_id'])
        self.assertEqual([e['event'] for e in events], ['progress', 'progress', 'done'])
        self.assertEqual(events[-1]['data'], {'state': 'completed', 'error_kind': None, 'reply': '接回後的回覆'})
        self.assertEqual(runner.resumed, [(body['request_id'], {'bridge_turn': 'b-' + body['request_id'],
                                                                'epoch': 'e1'})])
        turn = client.get('/api/turns/' + body['request_id']).json()['turn']
        self.assertEqual(turn['state'], 'completed')
        self.assertNotIn('bridge_record', turn)

    def test_restart_reattach_outcomes(self):
        cases = [(Interrupted(), 'interrupted'), (Unknown('bridge_restarted'), 'unknown'),
                 (Failed('timeout'), 'failed'), (None, 'unknown')]
        for resume_with, state in cases:
            with self.subTest(resume_with=type(resume_with).__name__):
                body = self.start_recorded_turn_and_shut_down()
                runner = RecordingRunner(resume_with=resume_with)
                with PairedClient(create_app(self.settings, runner=runner)) as client:
                    self.assertEqual(read_events(client, body['request_id'])[-1]['data']['state'], state)
                self.assertEqual(len(runner.resumed), 1)

    def test_restart_cannot_reattach_without_runner_or_with_fake_runner(self):
        for runner in (None, FakeRunner(steps=1, tick=0.01)):
            with self.subTest(runner=type(runner).__name__):
                body = self.start_recorded_turn_and_shut_down()
                with PairedClient(create_app(self.settings, runner=runner)) as client:
                    self.assertEqual(read_events(client, body['request_id'])[-1]['data']['state'], 'unknown')

    def test_restart_with_unreadable_record_is_unknown(self):
        for record in ('[1, 2', '[1, 2]'):  # 不是 JSON、不是物件
            with self.subTest(record=record):
                body = self.start_recorded_turn_and_shut_down()
                connection = db.connect(db.database_path(self.settings.state_dir))
                try:
                    connection.execute('UPDATE turns SET bridge_record = ? WHERE id = ?', (record, body['request_id']))
                finally:
                    connection.close()
                runner = RecordingRunner(resume_with='不該被呼叫')
                with PairedClient(create_app(self.settings, runner=runner)) as client:
                    self.assertEqual(read_events(client, body['request_id'])[-1]['data']['state'], 'unknown')
                self.assertEqual(runner.resumed, [])

    def test_conversation_shows_messages_and_replies_after_restart(self):
        body = self.body(text='第一個問題')
        with PairedClient(create_app(self.settings, runner=FakeRunner(steps=1, tick=0.01))) as first:
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

    def test_conversation_belongs_to_one_member(self):
        client = self.client(runner=FakeRunner(steps=1, tick=0.01))
        first = self.body()
        client.post('/api/turns', json=first)
        read_events(client, first['request_id'])
        other_member = add_member(self.settings.state_dir, name='成員二')
        wrong = self.body(conversation_id=first['conversation_id'], member=other_member)
        response = client.post('/api/turns', json=wrong)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['detail'], '這段對話屬於另一位成員，請開新對話')
        # 被擋下的請求什麼都沒留下：對話沒有多出回合，請求 ID 也沒被佔用。
        self.assertEqual(client.get('/api/turns/' + wrong['request_id']).status_code, 404)
        self.assertEqual(len(client.get('/api/conversations/' + first['conversation_id']).json()['turns']), 1)
        self.assertEqual(client.post('/api/turns', json={**wrong, 'conversation_id': str(uuid.uuid4())}).status_code,
                         202)
        # 原本的成員照樣可以續問。
        again = self.body(conversation_id=first['conversation_id'])
        self.assertEqual(client.post('/api/turns', json=again).status_code, 202)
        read_events(client, again['request_id'])
        # 對話刪掉之後，同一個對話 ID 可以給別的成員用。
        self.assertEqual(client.delete('/api/conversations/' + first['conversation_id']).status_code, 204)
        reused = self.body(conversation_id=first['conversation_id'], member=other_member)
        self.assertEqual(client.post('/api/turns', json=reused).status_code, 202)

    def test_conversation_list(self):
        client = self.client(runner=FakeRunner(steps=1, tick=0.01))
        self.assertEqual(client.get('/api/conversations').json(), {'conversations': []})
        long_text = '第一行\n\n  第二行   ' + '長' * 400
        older = self.body(text=long_text)
        client.post('/api/turns', json=older)
        read_events(client, older['request_id'])
        other_member = add_member(self.settings.state_dir, name='成員二')
        newer = self.body(text='短訊息', member=other_member)
        client.post('/api/turns', json=newer)
        read_events(client, newer['request_id'])
        listed = client.get('/api/conversations').json()['conversations']
        self.assertEqual([item['id'] for item in listed], [newer['conversation_id'], older['conversation_id']])
        self.assertEqual(listed[0], {'id': newer['conversation_id'], 'title': '短訊息', 'turns': 1,
                                     'member': other_member, 'member_name': '成員二', 'state': 'completed',
                                     'updated': listed[0]['updated']})
        # 最後活動時間是最後一個回合結束的時間（還沒結束就是開始的時間）。
        finished = client.get('/api/turns/' + newer['request_id']).json()['turn']
        self.assertEqual(listed[0]['updated'], finished['finished'])
        self.assertGreater(finished['finished'], finished['started'])
        # 標題只有第一則訊息的開頭：空白併成一個，超過長度加刪節號；清單不含訊息全文與回覆。
        self.assertEqual(listed[1]['title'], ('第一行 第二行 ' + '長' * 400)[:60] + '…')
        self.assertNotIn('長' * 61, json.dumps(listed, ensure_ascii=False))
        self.assertNotIn('reply', listed[1])
        # 續問之後：回合數加一，排到最前面，標題仍是第一則訊息，狀態是最後一個回合的。
        follow = self.body(conversation_id=older['conversation_id'], text='續問')
        blocking = self.client(runner=BlockingRunner())
        blocking.post('/api/turns', json=follow)
        listed = blocking.get('/api/conversations').json()['conversations']
        self.assertEqual([item['id'] for item in listed], [older['conversation_id'], newer['conversation_id']])
        self.assertEqual((listed[0]['turns'], listed[0]['state'], listed[0]['member_name']), (2, 'running', '成員一'))
        self.assertTrue(listed[0]['title'].startswith('第一行 第二行'))
        # 成員刪除後，清單照樣顯示當時的名稱；刪除對話後從清單消失。
        self.assertEqual(blocking.delete('/api/members/' + other_member).status_code, 204)
        self.assertEqual(blocking.delete('/api/conversations/' + newer['conversation_id']).status_code, 204)
        listed = blocking.get('/api/conversations').json()['conversations']
        self.assertEqual([item['id'] for item in listed], [older['conversation_id']])

    def test_conversation_list_requires_pairing(self):
        with PairedClient(create_app(self.settings, runner=FakeRunner()), pair=False) as client:
            self.assertEqual(client.get('/api/conversations').status_code, 401)

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
        self.assertEqual([e['event'] for e in events][-2:], ['stopping', 'done'])  # 送達後先告知「中斷中」
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
        client = self.client(runner=RaisingRunner(TimeoutError('provider socket timed out')))
        body = self.body()
        client.post('/api/turns', json=body)
        self.assertEqual(read_events(client, body['request_id'])[-1]['data']['error_kind'], 'internal_error')

    def test_runner_outcomes_map_to_fixed_states(self):
        cases = [(None, ('failed', 'internal_error')),  # 沒交出回覆就返回
                 (Failed('timeout'), ('failed', 'timeout')),
                 (Failed('quota exceeded: raw text'), ('failed', 'internal_error')),  # 不在固定分類
                 (Unknown('transport'), ('unknown', None)),
                 (Interrupted(), ('interrupted', None))]
        for error, expected in cases:
            with self.subTest(error=repr(error)):
                client = self.client(runner=RaisingRunner(error))
                body = self.body()
                client.post('/api/turns', json=body)
                done = read_events(client, body['request_id'])[-1]['data']
                self.assertEqual((done['state'], done['error_kind']), expected)

    def test_save_raises_when_the_reply_was_not_stored(self):
        class DoubleSaveRunner(Runner):
            second = None

            async def run(self, turn, hooks):
                hooks.save('第一次')
                try:
                    hooks.save('第二次')  # 回合已完成，不會存下；轉接器不可以據此通知遠端丟掉回覆
                except Exception as exc:
                    DoubleSaveRunner.second = type(exc).__name__

        client = self.client(runner=DoubleSaveRunner())
        body = self.body()
        client.post('/api/turns', json=body)
        self.assertEqual(read_events(client, body['request_id'])[-1]['data']['reply'], '第一次')
        self.assertEqual(DoubleSaveRunner.second, 'RuntimeError')
        turn = client.get('/api/turns/' + body['request_id']).json()['turn']
        self.assertEqual((turn['state'], turn['reply']), ('completed', '第一次'))

    def test_reply_over_limit_fails_without_storing_anything(self):
        self.assertEqual(MAX_REPLY_BYTES, 100_000)  # FR-2 預設 100 KB，UTF-8 位元組
        cases = [('x' * 100_000, 'completed'), ('中' * 33_333, 'completed'),  # 100,000／99,999 位元組
                 ('x' * 100_001, 'failed'), ('中' * 33_334, 'failed')]  # 100,001／100,002 位元組；中文字數仍少於上限
        for reply, state in cases:
            with self.subTest(chars=len(reply), bytes=len(reply.encode())):
                runner = ReplyRunner(reply)
                client = self.client(runner=runner)
                body = self.body()
                client.post('/api/turns', json=body)
                done = read_events(client, body['request_id'])[-1]['data']
                turn = client.get('/api/turns/' + body['request_id']).json()['turn']
                listed = client.get('/api/conversations/' + body['conversation_id']).json()['turns']
                self.assertIsNone(runner.save_raised)  # 兩種結果都寫進去了，轉接器可以照常 ack
                if state == 'completed':
                    self.assertEqual((done['state'], done['error_kind'], done['reply']), ('completed', None, reply))
                    self.assertEqual(turn['reply'], reply)
                else:
                    # 明確告知、不截斷：沒有回覆，也沒有截斷後的內容。
                    self.assertEqual(done, {'state': 'failed', 'error_kind': 'reply_too_long', 'reply': None})
                    self.assertEqual((turn['state'], turn['error_kind'], turn['reply']),
                                     ('failed', 'reply_too_long', None))
                    self.assertEqual([t['reply'] for t in listed], [None])

    def test_interrupt_that_does_not_reach_runner_is_reported(self):
        client = self.client(runner=UnreachableStopRunner())
        body = self.body()
        client.post('/api/turns', json=body)
        read_events_until(client, body['request_id'], 1)
        response = client.post('/api/turns/%s/interrupt' % body['request_id'])
        self.assertEqual((response.status_code, response.json()['turn']['state']), (502, 'running'))
        self.assertEqual([e['event'] for e in read_events_until(client, body['request_id'], 1)], ['progress'])
        self.assertEqual(client.get('/api/turns/' + body['request_id']).json()['turn']['state'], 'running')

    def test_without_runner_turns_are_refused_and_nothing_is_stored(self):
        client = PairedClient(create_app(self.settings))
        with client:
            body = self.body()
            self.assertEqual(client.post('/api/turns', json=body).status_code, 503)
            self.assertEqual(client.get('/api/turns/' + body['request_id']).status_code, 404)

    def test_fake_turns_setting_enables_fake_runner(self):
        client = PairedClient(create_app(Settings('127.0.0.1', 8420, self.settings.state_dir, fake_turns=True)))
        with client:
            self.assertEqual(client.post('/api/turns', json=self.body()).status_code, 202)

    def test_turn_uses_the_member_settings(self):
        class Capturing(Runner):
            seen = []

            async def run(self, turn, hooks):
                Capturing.seen.append(turn)
                hooks.save('ok')

        client = self.client(runner=Capturing())
        created = client.post('/api/members', json={
            'request_id': str(uuid.uuid4()), 'adapter': 'grok', 'name': 'Grok 深度', 'model': 'grok-4',
            'effort': 'high', 'auth_mode': 'subscription_cli', 'timeout_minutes': 30}).json()['member']
        body = self.body(member=created['id'])
        self.assertEqual(client.post('/api/turns', json=body).status_code, 202)
        read_events(client, body['request_id'])
        [turn] = Capturing.seen
        self.assertEqual((turn.member, turn.timeout, turn.adapter, turn.model, turn.effort, turn.auth_mode),
                         (created['id'], 1800, 'grok', 'grok-4', 'high', 'subscription_cli'))
        row = client.get('/api/turns/' + body['request_id']).json()['turn']
        self.assertEqual((row['member_name'], row['adapter']), ('Grok 深度', 'grok'))

    def test_missing_or_disabled_member_is_refused_and_nothing_is_stored(self):
        client = self.client()
        disabled = add_member(self.settings.state_dir, enabled=False)
        for member, status in ((str(uuid.uuid4()), 422), (disabled, 409)):
            with self.subTest(status=status):
                body = self.body(member=member)
                self.assertEqual(client.post('/api/turns', json=body).status_code, status)
                self.assertEqual(client.get('/api/turns/' + body['request_id']).status_code, 404)
                # 沒有留下請求登記：成員可以用之後，同一個請求可以重送成功。
        client.patch('/api/members/' + disabled, json={'enabled': True})
        self.assertEqual(client.post('/api/turns', json=body).status_code, 202)

    def test_resend_after_member_is_disabled_returns_the_original_turn(self):
        client = self.client()
        body = self.body()
        client.post('/api/turns', json=body)
        read_events(client, body['request_id'])
        client.patch('/api/members/' + self.member, json={'enabled': False})
        resent = client.post('/api/turns', json=body)
        self.assertEqual((resent.status_code, resent.json()['turn']['state']), (200, 'completed'))

    def test_member_whose_adapter_has_no_runner_is_refused(self):
        client = self.client(runner={'grok': FakeRunner(steps=1, tick=0.01)})  # 成員是 codex
        body = self.body()
        self.assertEqual(client.post('/api/turns', json=body).status_code, 503)
        self.assertEqual(client.get('/api/turns/' + body['request_id']).status_code, 404)
        grok = add_member(self.settings.state_dir, adapter='grok')
        other = self.body(member=grok)
        self.assertEqual(client.post('/api/turns', json=other).status_code, 202)
        self.assertEqual(read_events(client, other['request_id'])[-1]['data']['state'], 'completed')

    def test_invalid_requests_are_rejected(self):
        client = self.client()
        for changes in ({'request_id': 'not-a-uuid'}, {'conversation_id': 'x'}, {'member': ''}, {'member': 'm1'},
                        {'text': ''}, {'text': 'a' * (MAX_MESSAGE_CHARS + 1)}, {'extra': 1}):
            with self.subTest(changes=list(changes)):
                self.assertEqual(client.post('/api/turns', json=self.body(**changes)).status_code, 422)
        self.assertEqual(client.get('/api/turns/' + str(uuid.uuid4())).status_code, 404)
        self.assertEqual(client.get('/api/turns/%s/events' % uuid.uuid4()).status_code, 404)


class InterruptBeforeStartTest(unittest.TestCase):
    """中斷在回合工作開始執行前就送到：轉接器一開始就照辦，沒有做任何工作，回合標為已中斷。"""

    def test_interrupt_before_runner_starts(self):
        from app.web.turns import TurnRequest, TurnService

        with tempfile.TemporaryDirectory(prefix='yiqunren-interrupt-test-') as temporary:
            path = db.prepare(Path(temporary) / 'state')
            member = add_member(Path(temporary) / 'state')

            class OrderRecordingRunner(FakeRunner):
                calls = []

                async def run(self, turn, hooks):
                    self.calls.append('run')
                    await super().run(turn, hooks)

                async def stop(self, turn_id):
                    self.calls.append('stop')
                    await super().stop(turn_id)

            # 沒被中斷的話，0.01 秒後就會有進度並完成。
            runner = OrderRecordingRunner(steps=1, tick=0.01)

            async def scenario():
                service = TurnService(path, runner)
                body = TurnRequest(request_id=str(uuid.uuid4()), conversation_id=str(uuid.uuid4()),
                                   member=member, text='hi')
                self.assertEqual(service.start(body)[0], 202)
                self.assertEqual((await service.interrupt(body.request_id))[0], 202)
                await asyncio.sleep(0.05)
                return service.get(body.request_id)['state'], service.events_after(body.request_id, 0)

            state, events = asyncio.run(scenario())
        self.assertEqual(runner.calls, ['stop', 'run'])  # 中斷送到時，回合工作還沒開始執行
        self.assertEqual(state, 'interrupted')
        self.assertEqual(events, [(1, 'stopping', {}), (2, 'done', {'state': 'interrupted', 'error_kind': None})])


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
