"""FastAPI app 的離線驗收：健康檢查、資料庫建立、API 文件頁關閉、遙測不外送（NFR-4）。"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

from fastapi.testclient import TestClient

from app.storage import db
from app.web.config import Settings
from app.web.server import create_app


ROOT = Path(__file__).resolve().parents[1]


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='yiqunren-web-test-')
        self.addCleanup(self.temporary.cleanup)
        self.state = Path(self.temporary.name) / 'state'
        self.settings = Settings(host='127.0.0.1', port=8420, state_dir=self.state)

    def test_health_reports_schema_version_and_creates_database(self):
        with TestClient(create_app(self.settings)) as client:
            response = client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok', 'schema_version': db.SCHEMA_VERSION})
        self.assertTrue((self.state / db.DB_NAME).is_file())

    def test_interactive_docs_are_disabled(self):
        with TestClient(create_app(self.settings)) as client:
            for path in ('/docs', '/redoc', '/openapi.json'):
                with self.subTest(path=path):
                    self.assertEqual(client.get(path).status_code, 404)

    def test_bad_state_dir_stops_startup(self):
        self.state.mkdir(mode=0o755)
        os.chmod(self.state, 0o755)
        with self.assertRaises(db.StorageError):
            with TestClient(create_app(self.settings)):
                pass


class _Collector(BaseHTTPRequestHandler):
    posts = []

    def do_POST(self):
        self.rfile.read(int(self.headers.get('Content-Length') or 0))
        _Collector.posts.append(self.path)
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass


CHILD = r"""
import sys
from pathlib import Path
from fastapi.testclient import TestClient
from app.web.config import Settings
from app.web.server import create_app
with TestClient(create_app(Settings('127.0.0.1', 8420, Path(sys.argv[1])))) as client:
    for _ in range(10):
        assert client.get('/api/health').status_code == 200
        client.get('/missing')
"""


class TelemetryTest(unittest.TestCase):
    def test_no_export_even_when_environment_asks_for_it(self):
        collector = ThreadingHTTPServer(('127.0.0.1', 0), _Collector)
        threading.Thread(target=collector.serve_forever, daemon=True).start()
        self.addCleanup(collector.server_close)
        self.addCleanup(collector.shutdown)
        _Collector.posts = []
        with tempfile.TemporaryDirectory(prefix='yiqunren-telemetry-test-') as temporary:
            env = {**os.environ,
                   'FASTAPI_OTEL_AUTO_CONFIGURE': 'true',
                   'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://127.0.0.1:%d' % collector.server_port,
                   'OTEL_SERVICE_NAME': 'yiqunren-test',
                   'OTEL_METRIC_EXPORT_INTERVAL': '200', 'OTEL_BSP_SCHEDULE_DELAY': '100'}
            child = subprocess.run([sys.executable, '-c', CHILD, str(Path(temporary) / 'state')],
                                   cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(child.returncode, 0, child.stderr)
        self.assertEqual(_Collector.posts, [])
        # 若沒有明確關閉，FastAPI 會嘗試自動設定遙測，並在缺少外送套件時記一行錯誤。
        self.assertNotIn('telemetry', child.stderr.lower())


if __name__ == '__main__':
    unittest.main()
