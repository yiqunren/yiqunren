"""網頁介面的靜態檔與安全標頭（NFR-3）的離線驗收；用臨時目錄裡的假頁面，不需要先打包前端。"""
from pathlib import Path
import re
import tempfile
import unittest

from app.web import security
from app.web.config import Settings
from app.web.server import create_app
from web_client import PairedClient


ROOT = Path(__file__).resolve().parents[1]
INDEX = '<!doctype html><title>test page</title><script type="module" src="/assets/app.js"></script>'


class StaticPagesTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='yiqunren-static-test-')
        self.addCleanup(self.temporary.cleanup)
        base = Path(self.temporary.name)
        self.settings = Settings(host='127.0.0.1', port=8420, state_dir=base / 'state')
        self.static = base / 'static'
        (self.static / 'assets').mkdir(parents=True)
        (self.static / 'index.html').write_text(INDEX, encoding='utf-8')
        (self.static / 'assets' / 'app.js').write_text('console.log("page")', encoding='utf-8')
        (base / 'secret.txt').write_text('outside the static directory', encoding='utf-8')

    def client(self, *, pair=False, static=True):
        client = PairedClient(create_app(self.settings, static_dir=self.static if static else self.static / 'none'),
                              pair=pair)
        client.__enter__()
        self.addCleanup(client.__exit__, None, None, None)
        return client

    def test_page_files_are_readable_without_pairing_but_the_api_is_not(self):
        client = self.client()
        page = client.get('/')
        self.assertEqual((page.status_code, page.text), (200, INDEX))
        self.assertTrue(page.headers['content-type'].startswith('text/html'))
        script = client.get('/assets/app.js')
        self.assertEqual((script.status_code, script.text), (200, 'console.log("page")'))
        self.assertIn('javascript', script.headers['content-type'])
        self.assertEqual(client.head('/').status_code, 200)
        self.assertEqual(client.get('/assets/none.js').status_code, 404)
        # API 照舊要配對，不存在的 API 路徑也一樣。
        for path in ('/api/members', '/api/adapters', '/api/missing'):
            with self.subTest(path=path):
                self.assertEqual(client.get(path).status_code, 401)
        # 頁面檔只能讀取：沒配對時改變狀態的請求一律擋下。
        for method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            with self.subTest(method=method):
                self.assertEqual(client.request(method, '/').status_code, 401)
                self.assertEqual(client.request(method, '/assets/app.js').status_code, 401)

    def test_page_files_still_go_through_the_host_check(self):
        client = self.client()
        self.assertEqual(client.get('/', headers={'host': 'evil.example:8420'}).status_code, 400)

    def test_files_outside_the_static_directory_are_not_served(self):
        client = self.client(pair=True)
        for path in ('/%2e%2e/secret.txt', '/assets/%2e%2e/%2e%2e/secret.txt', '/..%2fsecret.txt',
                     '/%2e%2e/state/state.sqlite3'):
            with self.subTest(path=path):
                response = client.get(path)
                self.assertEqual(response.status_code, 404)
                self.assertNotIn('outside the static directory', response.text)

    def test_every_response_carries_the_security_headers(self):
        client = self.client()
        responses = {
            'page': client.get('/'),
            'script': client.get('/assets/app.js'),
            'api': client.get('/api/health'),
            'unpaired': client.get('/api/members'),
            'bad host': client.get('/', headers={'host': 'evil.example:8420'}),
            'missing': client.get('/nothing-here'),
            'no csrf header': client.post('/api/pair', json={'code': 'x'}, headers={security.CSRF_HEADER: '0'}),
        }
        self.assertEqual([r.status_code for r in responses.values()], [200, 200, 200, 401, 400, 404, 403])
        for name, response in responses.items():
            with self.subTest(response=name):
                policy = dict(part.strip().split(' ', 1) for part in
                              response.headers['content-security-policy'].split(';'))
                self.assertEqual(policy['default-src'], "'self'")
                self.assertEqual(policy['script-src'], "'self'")
                self.assertEqual(policy['style-src'], "'self'")
                self.assertEqual(policy['connect-src'], "'self'")
                self.assertEqual(policy['frame-ancestors'], "'none'")
                self.assertEqual(policy['object-src'], "'none'")
                self.assertEqual(policy['base-uri'], "'none'")
                self.assertNotIn('unsafe', response.headers['content-security-policy'])
                self.assertNotIn('*', response.headers['content-security-policy'])
                self.assertEqual(response.headers['x-content-type-options'], 'nosniff')
                # 不能是 no-referrer：瀏覽器會把同源 POST 的 Origin 送成 null，被 CSRF 檢查擋下。
                self.assertEqual(response.headers['referrer-policy'], 'same-origin')

    def test_without_a_built_frontend_the_root_explains_and_the_api_works(self):
        client = self.client(static=False)
        response = client.get('/')
        self.assertEqual(response.status_code, 404)
        self.assertIn('npm run build', response.json()['detail'])
        self.assertEqual(client.get('/api/health').status_code, 200)


class FrontendSourceRulesTest(unittest.TestCase):
    """前端原始碼的規則：AI 與使用者的文字一律當純文字顯示（NFR-3），頁面要能在內容安全政策下運作。"""

    def sources(self):
        files = [path for path in (ROOT / 'frontend' / 'src').rglob('*') if path.suffix in ('.ts', '.tsx')]
        self.assertTrue(files, '找不到前端原始碼')
        return files

    def test_no_raw_html_injection(self):
        banned = re.compile(r'dangerouslySetInnerHTML|\.innerHTML|\.outerHTML|insertAdjacentHTML|document\.write'
                            r'|\beval\(|new Function\(')
        for path in self.sources():
            if '.test.' in path.name:
                continue
            with self.subTest(path=path.name):
                self.assertIsNone(banned.search(path.read_text(encoding='utf-8')))

    def test_entry_page_has_no_inline_script_or_style(self):
        page = (ROOT / 'frontend' / 'index.html').read_text(encoding='utf-8')
        self.assertEqual(re.findall(r'<script(?![^>]*\bsrc=)[^>]*>', page), [])
        self.assertNotRegex(page, r'<style\b')
        self.assertNotRegex(page, r'\sstyle=')
        self.assertNotRegex(page, r'\son[a-z]+=')
        self.assertNotRegex(page, r'https?://')  # 不從外部載入任何東西


if __name__ == '__main__':
    unittest.main()
