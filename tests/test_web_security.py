"""NFR-3 本機安全的離線驗收：Host、配對與 Cookie、CSRF、請求大小與頻率限制；只用臨時目錄與假轉接器。"""
import contextlib
import io
import json
from pathlib import Path
import re
import tempfile
import unittest
import uuid

from app.storage import db, pairing
from app.web import security
from app.web.__main__ import main
from app.web.config import Settings
from app.web.fake_runner import FakeRunner
from app.web.server import create_app
from app.web.turns import MAX_MESSAGE_CHARS
from test_web_turns import add_member
from web_client import PairedClient, pair as pair_client


CSRF = {security.CSRF_HEADER: '1'}
COOKIE = security.cookie_name(8420)


class Clock:
    def __init__(self, now=1_000_000.0):
        self.now = now

    def __call__(self):
        return self.now


def wrong(code):
    """格式正確、但和 code 不同的配對碼。"""
    first = 'A' if code[0] != 'A' else 'B'
    return first + code[1:]


class SecurityTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='yiqunren-security-test-')
        self.addCleanup(self.temporary.cleanup)
        self.state = Path(self.temporary.name) / 'state'
        self.settings = Settings(host='127.0.0.1', port=8420, state_dir=self.state)
        self.member = add_member(self.state)
        self.clock = Clock()
        self.env = {'YIQUNREN_STATE_DIR': str(self.state)}

    def client(self, *, pair=True, csrf=True):
        client = PairedClient(create_app(self.settings, runner=FakeRunner(steps=1, tick=0.01), clock=self.clock),
                              pair=False, csrf=csrf)
        client.__enter__()
        self.addCleanup(client.__exit__, None, None, None)
        if pair:
            pair_client(client, now=self.clock.now)
        return client

    def code(self):
        return security.issue_code(db.database_path(self.state), now=self.clock.now)

    def redeem(self, client, code, headers=CSRF):
        return client.post('/api/pair', json={'code': code}, headers=headers)

    def member_name(self, client):
        return client.get('/api/members/' + self.member).json()['member']['name']

    def turn_body(self, **changes):
        return {'request_id': str(uuid.uuid4()), 'conversation_id': str(uuid.uuid4()), 'member': self.member,
                'text': 'hello', **changes}

    # Host（防 DNS rebinding）

    def test_host_must_be_an_ip_or_localhost_with_the_configured_port(self):
        client = self.client()
        for host in ('testserver', 'evil.example:8420', 'localhost.evil.example:8420', '127.0.0.1.nip.io:8420',
                     '127.0.0.1:8421', '127.0.0.1', 'localhost', '[::1]:9999', '[zz]:8420', '127.1:8420',
                     '127.0.0.1:8420:1', 'user@127.0.0.1:8420'):
            with self.subTest(host=host):
                self.assertEqual(client.get('/api/health', headers={'host': host}).status_code, 400)
                # 帶了有效的 Cookie 也一樣擋。
                self.assertEqual(client.get('/api/members', headers={'host': host}).status_code, 400)
        for host in ('127.0.0.1:8420', 'localhost:8420', 'LOCALHOST:8420', '[::1]:8420', '192.168.1.5:8420'):
            with self.subTest(host=host):
                self.assertEqual(client.get('/api/members', headers={'host': host}).status_code, 200)

    # 配對與 Cookie

    def test_unpaired_requests_are_refused_and_nothing_changes(self):
        client = self.client(pair=False)
        turn = self.turn_body()
        member_body = {'request_id': str(uuid.uuid4()), 'adapter': 'codex', 'name': '新成員', 'auth_mode': 'api_key'}
        member_path = '/api/members/' + self.member
        turn_path = '/api/turns/' + turn['request_id']
        conversation_path = '/api/conversations/' + turn['conversation_id']
        calls = [('GET', '/api/members', None), ('GET', member_path, None), ('POST', '/api/members', member_body),
                 ('PATCH', member_path, {'name': '改名'}), ('DELETE', member_path, None),
                 ('POST', '/api/turns', turn), ('GET', turn_path, None), ('GET', turn_path + '/events', None),
                 ('POST', turn_path + '/interrupt', None), ('GET', conversation_path, None),
                 ('DELETE', conversation_path, None), ('GET', '/missing', None)]
        for cookie in (None, 'not-a-real-token'):
            client.cookies.clear()
            if cookie:
                client.cookies.set(COOKIE, cookie)
            for method, path, body in calls:
                with self.subTest(cookie=cookie, method=method, path=path):
                    self.assertEqual(client.request(method, path, json=body).status_code, 401)
        # 不必配對的端點。
        self.assertEqual(client.get('/api/health').status_code, 200)
        self.assertEqual(client.get('/api/session').json(), {'paired': False})
        # 配對後確認剛才的請求都沒有生效。
        client.cookies.clear()
        pair_client(client, now=self.clock.now)
        self.assertEqual(client.get('/api/session').json(), {'paired': True})
        self.assertEqual([m['name'] for m in client.get('/api/members').json()['members']], ['成員一'])
        self.assertEqual(client.get(turn_path).status_code, 404)

    def test_pairing_code_is_one_time_and_accepts_lowercase_dashes_and_spaces(self):
        client = self.client(pair=False)
        code = self.code()
        self.assertRegex(code, r'^[23456789ABCDEFGHJKLMNPQRSTUVWXYZ]{4}-[23456789ABCDEFGHJKLMNPQRSTUVWXYZ]{4}$')
        response = self.redeem(client, ' ' + code.lower().replace('-', ' ') + ' ')
        self.assertEqual((response.status_code, response.json()), (200, {'paired': True}))
        self.assertEqual(client.get('/api/members').status_code, 200)
        client.cookies.clear()
        self.assertEqual(self.redeem(client, code).status_code, 403)  # 只能用一次
        self.assertEqual(client.get('/api/members').status_code, 401)

    def test_malformed_codes_are_rejected_without_counting_as_attempts(self):
        client = self.client(pair=False)
        code = self.code()
        for bad in ('', 'ABC', 'ABCD-EFG0', 'ABCD-EFGI', 'ABCDEFGHJ', 'x' * 33, 123, None):
            with self.subTest(bad=bad):
                self.assertEqual(self.redeem(client, bad).status_code, 422)
        self.assertEqual(client.post('/api/pair', json={'code': code, 'extra': 1}, headers=CSRF).status_code, 422)
        self.assertEqual(self.redeem(client, code).status_code, 200)

    def test_new_code_voids_the_old_one(self):
        client = self.client(pair=False)
        old = self.code()
        new = self.code()
        self.assertEqual(self.redeem(client, old).status_code, 403)
        self.assertEqual(self.redeem(client, new).status_code, 200)

    def test_five_wrong_attempts_void_the_code(self):
        client = self.client(pair=False)
        code = self.code()
        for _ in range(pairing.CODE_MAX_FAILURES - 1):
            self.assertEqual(self.redeem(client, wrong(code)).status_code, 403)
        self.assertEqual(self.redeem(client, code).status_code, 200)  # 錯 4 次還能用
        client.cookies.clear()
        code = self.code()
        for _ in range(pairing.CODE_MAX_FAILURES):
            self.assertEqual(self.redeem(client, wrong(code)).status_code, 403)
        self.assertEqual(self.redeem(client, code).status_code, 403)  # 錯滿 5 次就作廢
        self.assertEqual(client.get('/api/session').json(), {'paired': False})

    def test_code_expires_after_ten_minutes(self):
        client = self.client(pair=False)
        code = self.code()
        self.clock.now += pairing.CODE_TTL - 0.5
        self.assertEqual(self.redeem(client, code).status_code, 200)
        client.cookies.clear()
        code = self.code()
        self.clock.now += pairing.CODE_TTL
        self.assertEqual(self.redeem(client, code).status_code, 403)

    def test_cookie_attributes_and_only_hashes_are_stored(self):
        client = self.client(pair=False)
        code = self.code()
        response = self.redeem(client, code)
        header = response.headers['set-cookie']
        self.assertTrue(header.startswith(COOKIE + '='), header)
        attributes = {part.strip().lower() for part in header.split(';')[1:]}
        self.assertTrue({'httponly', 'samesite=strict', 'path=/', 'max-age=%d' % security.COOKIE_MAX_AGE}
                        <= attributes, attributes)
        self.assertFalse(any(a.startswith('domain') for a in attributes))
        token = client.cookies[COOKIE]
        self.assertGreaterEqual(len(token), 40)
        connection = db.connect(db.database_path(self.state))
        try:
            stored = [row[0] for row in connection.execute('SELECT token_hash FROM browser_sessions')]
        finally:
            connection.close()
        self.assertEqual(stored, [pairing.digest(token)])
        raw = b''.join(path.read_bytes() for path in self.state.iterdir() if path.name.startswith(db.DB_NAME))
        for secret in (token, code, code.replace('-', '')):
            self.assertNotIn(secret.encode(), raw)

    def test_session_expires_after_thirty_idle_days_and_use_renews_it(self):
        client = self.client()
        for _ in range(3):  # 每次都在 30 天內使用，就一直有效
            self.clock.now += pairing.SESSION_IDLE - 1
            self.assertEqual(client.get('/api/members').status_code, 200)
        self.clock.now += pairing.SESSION_IDLE + 1
        self.assertEqual(client.get('/api/members').status_code, 401)
        self.assertEqual(client.get('/api/session').json(), {'paired': False})
        self.assertFalse(security.has_sessions(db.database_path(self.state), now=self.clock.now))

    def test_logout_revokes_only_this_browser_and_unpair_revokes_all(self):
        client = self.client()
        first = client.cookies[COOKIE]
        client.cookies.clear()
        pair_client(client, now=self.clock.now)  # 第二個瀏覽器
        second = client.cookies[COOKIE]
        response = client.delete('/api/session')
        self.assertEqual(response.status_code, 204)
        self.assertIn('max-age=0', response.headers['set-cookie'].lower())
        self.assertEqual(client.get('/api/members').status_code, 401)
        client.cookies.set(COOKIE, second)  # 伺服器端也撤銷了，不只是瀏覽器刪掉 Cookie
        self.assertEqual(client.get('/api/members').status_code, 401)
        client.cookies.clear()
        client.cookies.set(COOKIE, first)
        self.assertEqual(client.get('/api/members').status_code, 200)
        # 本機指令撤銷所有瀏覽器，尚未使用的配對碼也作廢。
        pending = self.code()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(['unpair'], self.env), 0)
        self.assertIn('已撤銷 1 個', out.getvalue())
        self.assertEqual(client.get('/api/members').status_code, 401)
        self.assertEqual(self.redeem(client, pending).status_code, 403)

    def test_pair_command_prints_a_code_that_pairs_a_browser(self):
        client = self.client(pair=False)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(['pair'], self.env), 0)
        match = re.search(r'配對碼：([0-9A-Z]{4}-[0-9A-Z]{4})', out.getvalue())
        self.assertIsNotNone(match, out.getvalue())
        self.assertFalse(security.has_sessions(db.database_path(self.state), now=self.clock.now))
        self.assertEqual(self.redeem(client, match.group(1)).status_code, 200)
        self.assertTrue(security.has_sessions(db.database_path(self.state), now=self.clock.now))
        for argv in (['bogus'], ['pair', 'extra']):
            with self.subTest(argv=argv), contextlib.redirect_stderr(io.StringIO()) as err:
                self.assertEqual(main(argv, self.env), 2)
                self.assertIn('用法', err.getvalue())

    # CSRF

    def test_state_changing_requests_need_the_custom_header_and_same_origin(self):
        client = self.client(csrf=False)
        path = '/api/members/' + self.member
        refused = [{}, {security.CSRF_HEADER: '0'},
                   {**CSRF, 'Origin': 'http://127.0.0.1:3000'},       # 本機其他埠的網頁
                   {**CSRF, 'Origin': 'http://localhost:8420'},       # 和 Host（127.0.0.1:8420）不同源
                   {**CSRF, 'Origin': 'https://127.0.0.1:8420'},
                   {**CSRF, 'Origin': 'null'},
                   {**CSRF, 'Sec-Fetch-Site': 'same-site'},
                   {**CSRF, 'Sec-Fetch-Site': 'cross-site'},
                   {**CSRF, 'Sec-Fetch-Site': 'none'}]
        for headers in refused:
            with self.subTest(headers=headers):
                self.assertEqual(client.patch(path, json={'name': '被改了'}, headers=headers).status_code, 403)
        self.assertEqual(self.member_name(client), '成員一')  # 讀取不必帶自訂標頭
        body = self.turn_body()
        self.assertEqual(client.post('/api/turns', json=body).status_code, 403)
        self.assertEqual(client.get('/api/turns/' + body['request_id']).status_code, 404)
        self.assertEqual(client.delete('/api/session').status_code, 403)
        self.assertEqual(client.get('/api/session').json(), {'paired': True})
        self.assertEqual(self.redeem(client, self.code(), headers={}).status_code, 403)
        for headers in (CSRF, {**CSRF, 'Origin': 'http://127.0.0.1:8420', 'Sec-Fetch-Site': 'same-origin'}):
            with self.subTest(headers=headers):
                self.assertEqual(client.patch(path, json={'name': '改名'}, headers=headers).status_code, 200)

    # 大小

    def test_request_body_size_limit(self):
        client = self.client()
        json_headers = {'content-type': 'application/json'}
        over = b' ' * (security.MAX_BODY_BYTES - 1) + b'{}'
        self.assertEqual(client.post('/api/members', content=over, headers=json_headers).status_code, 413)
        exact = b' ' * (security.MAX_BODY_BYTES - 2) + b'{}'
        self.assertEqual(client.post('/api/members', content=exact, headers=json_headers).status_code, 422)

        def chunks():  # 沒有 Content-Length，邊讀邊算
            for _ in range(security.MAX_BODY_BYTES // 4096 + 1):
                yield b' ' * 4096
        self.assertEqual(client.post('/api/members', content=chunks(), headers=json_headers).status_code, 413)
        self.assertEqual(client.get('/api/members').json()['members'][0]['name'], '成員一')
        # 最長的訊息用最佔空間的 JSON 編碼（每個表情符號 12 位元組）也放得下。
        body = self.turn_body(text='\U0001F600' * MAX_MESSAGE_CHARS)
        content = json.dumps(body).encode()
        self.assertGreater(len(content), 12 * MAX_MESSAGE_CHARS)
        self.assertEqual(client.post('/api/turns', content=content, headers=json_headers).status_code, 202)

    # 頻率

    def test_rate_limits_for_state_changing_requests(self):
        client = self.client()  # 配對本身也算一次（時間 t0）
        self.clock.now += 1
        for _ in range(security.RATE_LIMIT_TURNS):
            self.assertEqual(client.post('/api/turns', json={}).status_code, 422)  # 內容不合格也計入
        response = client.post('/api/turns', json={})
        self.assertEqual((response.status_code, response.headers['retry-after']), (429, '60'))
        missing = '/api/members/' + str(uuid.uuid4())
        for _ in range(security.RATE_LIMIT_TOTAL - security.RATE_LIMIT_TURNS - 1):
            self.assertEqual(client.patch(missing, json={'name': 'x'}).status_code, 404)
        self.assertEqual(client.patch(missing, json={'name': 'x'}).status_code, 429)
        for _ in range(100):  # 讀取不限
            self.assertEqual(client.get('/api/members').status_code, 200)
        self.clock.now += 30
        for _ in range(5):
            response = client.patch(missing, json={'name': 'x'})
            self.assertEqual((response.status_code, response.headers['retry-after']), (429, '29'))
        # 視窗過了，額度全部回來；剛才被擋下的 5 次不計入。
        self.clock.now += 30.5
        for _ in range(security.RATE_LIMIT_TURNS):
            self.assertEqual(client.post('/api/turns', json={}).status_code, 422)
        for _ in range(security.RATE_LIMIT_TOTAL - security.RATE_LIMIT_TURNS):
            self.assertEqual(client.patch(missing, json={'name': 'x'}).status_code, 404)
        self.assertEqual(client.patch(missing, json={'name': 'x'}).status_code, 429)


if __name__ == '__main__':
    unittest.main()
