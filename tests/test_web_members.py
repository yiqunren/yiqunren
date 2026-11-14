"""FR-1 成員設定 HTTP 介面的離線驗收；只用臨時目錄與假轉接器，不呼叫任何 AI。"""
import asyncio
from pathlib import Path
import tempfile
import unittest
import uuid

from app.services import adapters
from app.web.config import Settings
from app.web.fake_runner import FakeRunner
from app.web.members import TERMS_NOTICE
from app.web.runner import Runner, Unknown
from app.web.server import create_app
from test_web_turns import read_events, read_events_until
from web_client import PairedClient


class BlockUntilStopped(Runner):
    def __init__(self):
        self.stopped = {}

    async def run(self, turn, hooks):
        hooks.progress({'step': 1})
        event = self.stopped.setdefault(turn.turn_id, asyncio.Event())
        await event.wait()
        raise Unknown('stop_unconfirmed')

    async def stop(self, turn_id):
        self.stopped.setdefault(turn_id, asyncio.Event()).set()


class MemberApiTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='yiqunren-members-test-')
        self.addCleanup(self.temporary.cleanup)
        self.settings = Settings(host='127.0.0.1', port=8420, state_dir=Path(self.temporary.name) / 'state')

    def client(self, runner=None):
        client = PairedClient(create_app(self.settings, runner=runner or FakeRunner(steps=1, tick=0.01)))
        client.__enter__()
        self.addCleanup(client.__exit__, None, None, None)
        return client

    def new(self, **changes):
        return {'request_id': str(uuid.uuid4()), 'adapter': 'codex', 'name': 'Codex 深度', 'auth_mode': 'api_key',
                **changes}

    def create(self, client, **changes):
        response = client.post('/api/members', json=self.new(**changes))
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()['member']

    def turn(self, client, member_id, **changes):
        body = {'request_id': str(uuid.uuid4()), 'conversation_id': str(uuid.uuid4()), 'member': member_id,
                'text': 'hello', **changes}
        return body, client.post('/api/turns', json=body)

    def test_create_with_defaults_and_read_back(self):
        client = self.client()
        member = self.create(client)
        self.assertEqual({key: member[key] for key in ('adapter', 'adapter_name', 'name', 'model', 'effort',
                                                       'auth_mode', 'timeout_minutes', 'enabled', 'status',
                                                       'terms_notice')},
                         {'adapter': 'codex', 'adapter_name': 'Codex', 'name': 'Codex 深度', 'model': '',
                          'effort': None, 'auth_mode': 'api_key', 'timeout_minutes': 15, 'enabled': True,
                          'status': 'idle', 'terms_notice': None})
        self.assertEqual(client.get('/api/members/' + member['id']).json()['member'], member)
        self.assertEqual(client.get('/api/members').json()['members'], [member])

    def test_full_settings_and_subscription_cli_notice(self):
        client = self.client()
        member = self.create(client, adapter='grok', name='  Grok 快速  ', model='grok-4.1-fast', effort='low',
                             auth_mode='subscription_cli', timeout_minutes=60)
        self.assertEqual((member['name'], member['model'], member['effort'], member['timeout_minutes']),
                         ('Grok 快速', 'grok-4.1-fast', 'low', 60))
        self.assertEqual(member['terms_notice'], TERMS_NOTICE)  # FR-1：訂閱 CLI 模式要提示服務條款

    def test_create_is_idempotent(self):
        client = self.client()
        body = self.new()
        first = client.post('/api/members', json=body)
        again = client.post('/api/members', json=body)
        self.assertEqual((first.status_code, again.status_code), (201, 200))
        self.assertEqual(again.json()['member']['id'], first.json()['member']['id'])
        self.assertEqual(client.post('/api/members', json={**body, 'name': 'other'}).status_code, 409)
        self.assertEqual(len(client.get('/api/members').json()['members']), 1)

    def test_invalid_settings_are_rejected_and_nothing_is_stored(self):
        client = self.client()
        cases = [{'adapter': 'nobody'}, {'adapter': 'claude_code', 'auth_mode': 'subscription_cli'},
                 {'auth_mode': 'magic'}, {'timeout_minutes': 0}, {'timeout_minutes': 61},
                 {'timeout_minutes': '5'}, {'timeout_minutes': 5.0}, {'timeout_minutes': True},
                 {'name': ''}, {'name': '   '}, {'name': 'a\nb'}, {'name': 'x' * 81},
                 {'model': 'bad model'}, {'model': '-x'}, {'model': 'm' * 101},
                 {'effort': 'High'}, {'effort': ''}, {'effort': 'x' * 21},
                 {'request_id': 'not-a-uuid'}, {'extra': 1}]
        for changes in cases:
            with self.subTest(changes=changes):
                self.assertEqual(client.post('/api/members', json=self.new(**changes)).status_code, 422)
        self.assertEqual(client.get('/api/members').json()['members'], [])

    def test_model_and_effort_only_when_the_adapter_supports_them(self):
        plain = adapters.Adapter(code='plainbot', name='Plain Bot', turn_fields=frozenset({'message'}),
                                 auth_modes=('api_key',), strengths=('測試',), weaknesses=('測試',),
                                 choose_when='測試用。')
        with adapters.override((*adapters.adapters(), plain)):
            client = self.client()
            self.assertEqual(client.post('/api/members', json=self.new(adapter='plainbot', model='m1')).status_code, 422)
            self.assertEqual(client.post('/api/members', json=self.new(adapter='plainbot', effort='low')).status_code,
                             422)
            member = self.create(client, adapter='plainbot')
            self.assertEqual(client.patch('/api/members/' + member['id'], json={'effort': 'low'}).status_code, 422)

    def test_update_settings_disable_and_enable(self):
        client = self.client()
        member = self.create(client, effort='high')
        response = client.patch('/api/members/' + member['id'],
                                json={'name': '改名', 'model': 'gpt-5.1', 'timeout_minutes': 30,
                                      'auth_mode': 'subscription_cli'})
        self.assertEqual(response.status_code, 200)
        updated = response.json()['member']
        self.assertEqual((updated['name'], updated['model'], updated['effort'], updated['timeout_minutes'],
                          updated['terms_notice']), ('改名', 'gpt-5.1', 'high', 30, TERMS_NOTICE))
        cleared = client.patch('/api/members/' + member['id'], json={'effort': None}).json()['member']
        self.assertIsNone(cleared['effort'])
        self.assertFalse(client.patch('/api/members/' + member['id'], json={'enabled': False}).json()['member']['enabled'])
        self.assertTrue(client.patch('/api/members/' + member['id'], json={'enabled': True}).json()['member']['enabled'])

    def test_invalid_updates_are_rejected_without_changes(self):
        client = self.client()
        member = self.create(client, adapter='claude_code')
        for changes in ({'adapter': 'grok'}, {'auth_mode': 'subscription_cli'}, {'name': None}, {'name': ''},
                        {'timeout_minutes': 0}, {'enabled': 'no'}, {'model': 'bad model'}):
            with self.subTest(changes=changes):
                self.assertEqual(client.patch('/api/members/' + member['id'], json=changes).status_code, 422)
        self.assertEqual(client.get('/api/members/' + member['id']).json()['member'], member)
        self.assertEqual(client.patch('/api/members/' + str(uuid.uuid4()), json={'name': 'x'}).status_code, 404)
        self.assertEqual(client.get('/api/members/' + str(uuid.uuid4())).status_code, 404)
        self.assertEqual(client.get('/api/members/not-a-uuid').status_code, 422)

    def test_delete_keeps_conversations_with_the_old_name(self):
        client = self.client()
        body = self.new(name='要刪的成員')
        member = client.post('/api/members', json=body).json()['member']
        turn, response = self.turn(client, member['id'])
        self.assertEqual(response.status_code, 202)
        read_events(client, turn['request_id'])
        self.assertEqual(client.delete('/api/members/' + member['id']).status_code, 204)
        self.assertEqual(client.get('/api/members/' + member['id']).status_code, 404)
        self.assertEqual(client.delete('/api/members/' + member['id']).status_code, 404)
        # 對話照樣保留，記著當時的成員名稱。
        listed = client.get('/api/conversations/' + turn['conversation_id']).json()['turns']
        self.assertEqual([(t['member'], t['member_name'], t['state']) for t in listed],
                         [(member['id'], '要刪的成員', 'completed')])
        # 刪除後用同一個請求重送：明確告知已刪除，不重新新增。
        self.assertEqual(client.post('/api/members', json=body).status_code, 410)
        # 刪掉的成員不能再送新回合。
        _, again = self.turn(client, member['id'])
        self.assertEqual(again.status_code, 422)

    def test_member_with_running_turn_cannot_be_deleted_and_status_follows_turns(self):
        runner = BlockUntilStopped()
        client = self.client(runner=runner)
        member = self.create(client)
        turn, _ = self.turn(client, member['id'])
        read_events_until(client, turn['request_id'], 1)
        self.assertEqual(client.get('/api/members/' + member['id']).json()['member']['status'], 'running')
        self.assertEqual(client.delete('/api/members/' + member['id']).status_code, 409)
        # 停用不影響已經在跑的回合（FR-1）。
        client.patch('/api/members/' + member['id'], json={'enabled': False})
        self.assertEqual(client.get('/api/turns/' + turn['request_id']).json()['turn']['state'], 'running')
        client.post('/api/turns/%s/interrupt' % turn['request_id'])
        self.assertEqual(read_events(client, turn['request_id'])[-1]['data']['state'], 'unknown')
        self.assertEqual(client.get('/api/members/' + member['id']).json()['member']['status'], 'needs_review')
        # 再送一個回合完成後回到閒置。
        client.patch('/api/members/' + member['id'], json={'enabled': True})
        runner.run = FakeRunner(steps=1, tick=0.01).run  # 之後的回合正常完成
        second, response = self.turn(client, member['id'])
        self.assertEqual(response.status_code, 202)
        self.assertEqual(read_events(client, second['request_id'])[-1]['data']['state'], 'completed')
        self.assertEqual(client.get('/api/members/' + member['id']).json()['member']['status'], 'idle')
        self.assertEqual(client.delete('/api/members/' + member['id']).status_code, 204)


class AdapterListTest(unittest.TestCase):
    """GET /api/adapters：成員設定可選的轉接器與支援項目，一律從登記處取得（NFR-7）。"""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='yiqunren-adapters-test-')
        self.addCleanup(self.temporary.cleanup)
        self.settings = Settings(host='127.0.0.1', port=8420, state_dir=Path(self.temporary.name) / 'state')

    def listed(self, runner):
        with PairedClient(create_app(self.settings, runner=runner)) as client:
            response = client.get('/api/adapters')
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_default_registry_in_order_with_only_the_listed_fields(self):
        # 完全相等：能力描述、模型等級、socket 位置、認證模式專屬欄位都不在回應裡。
        self.assertEqual(self.listed(FakeRunner(steps=1, tick=0.01)), {
            'adapters': [
                {'code': 'codex', 'name': 'Codex', 'auth_modes': ['api_key', 'subscription_cli'],
                 'supports_model': True, 'supports_effort': True, 'available': True},
                {'code': 'grok', 'name': 'Grok', 'auth_modes': ['api_key', 'subscription_cli'],
                 'supports_model': True, 'supports_effort': True, 'available': True},
                {'code': 'claude_code', 'name': 'Claude Code', 'auth_modes': ['api_key'],
                 'supports_model': True, 'supports_effort': True, 'available': True},
            ],
            'terms_notice': TERMS_NOTICE,
        })

    def test_available_follows_the_configured_runners(self):
        cases = [(None, []), ({'grok': FakeRunner(steps=1, tick=0.01)}, ['grok']),
                 (FakeRunner(steps=1, tick=0.01), list(adapters.codes()))]
        for runner, expected in cases:
            with self.subTest(runner=runner):
                listed = self.listed(runner)['adapters']
                self.assertEqual([a['code'] for a in listed if a['available']], expected)

    def test_registry_changes_show_up_and_match_what_members_accept(self):
        plain = adapters.Adapter(code='plainbot', name='Plain Bot', turn_fields=frozenset({'message'}),
                                 auth_modes=('api_key',), strengths=('測試',), weaknesses=('測試',),
                                 choose_when='測試用。')
        # 模型只出現在某個認證模式的專屬欄位：清單和新增成員的檢查要一致。
        moded = adapters.Adapter(code='modebot', name='Mode Bot', turn_fields=frozenset({'message'}),
                                 auth_modes=('api_key',), mode_fields={'api_key': frozenset({'model'})},
                                 strengths=('測試',), weaknesses=('測試',), choose_when='測試用。')
        with PairedClient(create_app(self.settings, runner={'plainbot': FakeRunner(steps=1, tick=0.01)})) as client:
            with adapters.override((*adapters.adapters(), plain, moded)):
                listed = {a['code']: a for a in client.get('/api/adapters').json()['adapters']}
                self.assertEqual(list(listed), [*adapters.codes()])
                self.assertEqual(listed['plainbot'], {'code': 'plainbot', 'name': 'Plain Bot', 'auth_modes': ['api_key'],
                                                      'supports_model': False, 'supports_effort': False,
                                                      'available': True})
                self.assertEqual((listed['modebot']['supports_model'], listed['modebot']['supports_effort'],
                                  listed['modebot']['available']), (True, False, False))
                for code, item in listed.items():
                    body = {'request_id': str(uuid.uuid4()), 'adapter': code, 'name': code, 'auth_mode': 'api_key'}
                    with self.subTest(code=code):
                        self.assertEqual(client.post('/api/members', json={**body, 'model': 'm1'}).status_code,
                                         201 if item['supports_model'] else 422)
                        self.assertEqual(client.post('/api/members', json={
                            **body, 'request_id': str(uuid.uuid4()), 'effort': 'low'}).status_code,
                            201 if item['supports_effort'] else 422)
            with adapters.override(adapters.adapters()[1:]):  # 移除第一家
                codes = [a['code'] for a in client.get('/api/adapters').json()['adapters']]
                self.assertEqual(codes, ['grok', 'claude_code'])

    def test_requires_pairing(self):
        with PairedClient(create_app(self.settings, runner=FakeRunner(steps=1, tick=0.01)), pair=False) as client:
            self.assertEqual(client.get('/api/adapters').status_code, 401)


if __name__ == '__main__':
    unittest.main()
