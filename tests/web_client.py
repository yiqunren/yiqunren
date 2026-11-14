"""測試用的 HTTP 客戶端：照 NFR-3 用本機位址連線，伺服器啟動後先用一次性配對碼配對，之後每個請求都帶 CSRF 標頭。"""
from fastapi.testclient import TestClient

from app.web import security


BASE_URL = 'http://127.0.0.1:8420'  # 測試的 Settings 都用 8420 埠


class PairedClient(TestClient):
    """pair=False 時只設好位址與 CSRF 標頭，不配對。"""

    def __init__(self, app, *, pair=True, csrf=True, **options):
        options.setdefault('base_url', BASE_URL)
        super().__init__(app, headers={security.CSRF_HEADER: '1'} if csrf else None, **options)
        self.pair = pair

    def __enter__(self):
        client = super().__enter__()
        if self.pair:
            pair(client)
        return client


def pair(client, *, now=None):
    response = client.post('/api/pair', json={'code': security.issue_code(client.app.state.db_path, now=now)},
                           headers={security.CSRF_HEADER: '1'})
    assert response.status_code == 200, response.text
    return response
