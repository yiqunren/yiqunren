"""FR-1 預設成員的離線驗收：資料庫第一次建立時每個轉接器建一位，只建一次；只用假轉接器與臨時目錄。"""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
import uuid

from app.services import adapters
from app.storage import db, requests
from app.web.__main__ import main
from app.web.config import Settings
from app.web.fake_runner import FakeRunner
from app.web.members import prepare_database
from app.web.server import create_app
from test_web_turns import read_events
from web_client import PairedClient


SETTINGS = {'adapter': None, 'adapter_name': None, 'name': None, 'model': '', 'effort': None, 'auth_mode': 'api_key',
            'timeout_minutes': 15, 'enabled': True, 'status': 'idle', 'terms_notice': None}


class DefaultMembersTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='yiqunren-default-members-test-')
        self.addCleanup(self.temporary.cleanup)
        self.state = Path(self.temporary.name) / 'state'
        self.settings = Settings(host='127.0.0.1', port=8420, state_dir=self.state)

    def client(self):
        client = PairedClient(create_app(self.settings, runner=FakeRunner(steps=1, tick=0.01)))
        client.__enter__()
        self.addCleanup(client.__exit__, None, None, None)
        return client

    def listed(self, client):
        return client.get('/api/members').json()['members']

    def count(self, table):
        connection = db.connect(db.database_path(self.state))
        try:
            return connection.execute('SELECT COUNT(*) FROM %s' % table).fetchone()[0]
        finally:
            connection.close()

    def test_first_start_creates_one_member_per_adapter_in_registry_order(self):
        listed = self.listed(self.client())
        expected = [{**SETTINGS, 'adapter': entry.code, 'adapter_name': entry.name, 'name': entry.name}
                    for entry in adapters.adapters()]
        self.assertEqual([{key: item[key] for key in SETTINGS} for item in listed], expected)
        self.assertEqual([item['name'] for item in listed], ['Codex', 'Grok', 'Claude Code', 'Claude（API）'])
        # 支援花費上限的（Claude Code、Claude（API）的 API key 模式）預設 1 美元，其他不設（FR-1）。
        self.assertEqual([item['max_budget_usd'] for item in listed], [None, None, 1.0, 1.0])
        self.assertEqual(len({item['id'] for item in listed}), 4)
        for item in listed:
            uuid.UUID(item['id'], version=4)

    def test_default_member_can_chat_right_after_pairing(self):
        client = self.client()
        member = self.listed(client)[0]
        body = {'request_id': str(uuid.uuid4()), 'conversation_id': str(uuid.uuid4()), 'member': member['id'],
                'text': '你好'}
        self.assertEqual(client.post('/api/turns', json=body).status_code, 202)
        self.assertEqual(read_events(client, body['request_id'])[-1]['data']['state'], 'completed')

    def test_created_only_once_and_owner_changes_are_kept(self):
        client = self.client()
        codex, grok, claude, claude_api = self.listed(client)
        self.assertEqual(client.patch('/api/members/' + codex['id'], json={'name': '改過的名字'}).status_code, 200)
        self.assertEqual(client.delete('/api/members/' + grok['id']).status_code, 204)
        client.__exit__(None, None, None)
        restarted = self.listed(self.client())  # 伺服器重啟
        self.assertEqual([(item['id'], item['name']) for item in restarted],
                         [(codex['id'], '改過的名字'), (claude['id'], 'Claude Code'), (claude_api['id'], 'Claude（API）')])

    def test_all_deleted_stays_empty_after_restart(self):
        client = self.client()
        for item in self.listed(client):
            self.assertEqual(client.delete('/api/members/' + item['id']).status_code, 204)
        client.__exit__(None, None, None)
        self.assertEqual(self.listed(self.client()), [])

    def test_existing_database_gets_no_defaults(self):
        db.prepare(self.state)  # 已經存在、沒有預設成員的資料庫（例如這個功能之前建立的）
        self.assertEqual(self.listed(self.client()), [])

    def test_upgraded_database_gets_no_defaults(self):
        self.state.mkdir(mode=0o700)
        path = db.database_path(self.state)
        path.touch(mode=0o600)
        connection = db.connect(path)
        for statement in db.MIGRATIONS[0]:
            connection.execute(statement)
        connection.execute('PRAGMA user_version = 1')
        connection.close()
        self.assertEqual(self.listed(self.client()), [])

    def test_upgrade_fills_default_spending_cap_only_where_supported(self):
        self.state.mkdir(mode=0o700)
        path = db.database_path(self.state)
        path.touch(mode=0o600)
        connection = db.connect(path)
        for version in range(7):  # 第 7 版：還沒有花費上限欄位
            for statement in db.MIGRATIONS[version]:
                connection.execute(statement)
        connection.execute('PRAGMA user_version = 7')
        rows = [('m-claude', 'claude_code', 'api_key'), ('m-codex', 'codex', 'api_key'),
                ('m-grok-cli', 'grok', 'subscription_cli'), ('m-gone', 'retired', 'api_key')]
        for number, (member_id, adapter, auth_mode) in enumerate(rows):
            connection.execute("INSERT INTO requests VALUES (?, 'member_create', 'h', 'claimed', 1, 1, NULL)",
                               (member_id,))
            connection.execute('INSERT INTO members (id, adapter, name, model, effort, auth_mode, timeout, enabled,'
                               " created, updated) VALUES (?, ?, ?, '', NULL, ?, 900, 1, ?, ?)",
                               (member_id, adapter, member_id, auth_mode, number, number))
        connection.commit()
        connection.close()
        prepare_database(self.state)
        connection = db.connect(path)
        try:
            found = dict(connection.execute('SELECT id, max_budget_usd FROM members').fetchall())
        finally:
            connection.close()
        # 升級不建預設成員；只有支援上限的既有成員補 1 美元，未登記的轉接器不動。
        self.assertEqual(found, {'m-claude': 1.0, 'm-codex': None, 'm-grok-cli': None, 'm-gone': None})
        prepare_database(self.state)  # 已是最新版：不再補值
        connection = db.connect(path)
        try:
            connection.execute("UPDATE members SET max_budget_usd = NULL WHERE id = 'm-claude'")
            connection.commit()
        finally:
            connection.close()
        prepare_database(self.state)
        connection = db.connect(path)
        try:
            self.assertIsNone(connection.execute("SELECT max_budget_usd FROM members WHERE id = 'm-claude'").fetchone()[0])
        finally:
            connection.close()

    def test_pair_command_creating_the_database_seeds_once(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['pair'], {'YIQUNREN_STATE_DIR': str(self.state)}), 0)
        self.assertEqual(self.count('members'), 4)
        self.assertEqual([item['name'] for item in self.listed(self.client())],
                         ['Codex', 'Grok', 'Claude Code', 'Claude（API）'])
        self.assertEqual(self.count('members'), 4)

    def test_failure_while_seeding_undoes_the_whole_creation(self):
        def broken(connection):
            connection.execute("INSERT INTO requests VALUES ('x', 'k', 'h', 'claimed', 1, 1, NULL)")
            raise RuntimeError('seeding failed')

        with self.assertRaises(RuntimeError):
            db.prepare(self.state, on_create=broken)
        connection = db.connect(db.database_path(self.state))
        try:
            self.assertEqual(db.schema_version(connection), 0)
            tables = connection.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
            self.assertEqual(tables, 0)
        finally:
            connection.close()
        # 下次啟動重新建立，預設成員照樣建好。
        prepare_database(self.state)
        self.assertEqual(self.count('members'), 4)
        self.assertEqual(self.count('requests'), 4)

    def test_adapter_without_api_key_mode_stops_creation(self):
        only_cli = adapters.Adapter(code='clionly', name='CLI Only', turn_fields=frozenset({'message'}),
                                    auth_modes=('subscription_cli',), strengths=('測試',), weaknesses=('測試',),
                                    choose_when='測試用。')
        with adapters.override(adapters.DEFAULT_ADAPTERS + (only_cli,)):
            with self.assertRaises(ValueError):
                prepare_database(self.state)
        connection = db.connect(db.database_path(self.state))
        try:
            self.assertEqual(db.schema_version(connection), 0)  # 整個建立撤銷，不會只建一半
        finally:
            connection.close()

    def test_default_members_have_their_own_request_records(self):
        prepare_database(self.state)
        connection = db.connect(db.database_path(self.state))
        try:
            rows = connection.execute('SELECT r.kind, r.state FROM members m JOIN requests r ON r.id = m.id').fetchall()
        finally:
            connection.close()
        self.assertEqual([(row['kind'], row['state']) for row in rows], [('member_default', requests.CLAIMED)] * 4)


if __name__ == '__main__':
    unittest.main()
