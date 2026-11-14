"""FastAPI app。只裝 fastapi＋uvicorn，並在建立 app 時明確關閉內建遙測（NFR-4）。"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
import time

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.storage import db
from app.web import bridges, config, members, security, turns
from app.web.fake_runner import FakeRunner


# 程式裡明確給的值會蓋過 FASTAPI_OTEL_AUTO_CONFIGURE 等環境變數，使用者環境怎麼設都不外送。
TELEMETRY_OFF = {'auto_configure': False, 'tracing': False, 'metrics': False, 'logs': False}
# 網頁介面打包後的靜態檔（在 frontend/ 執行 npm run build 產生，不進 Git）。
STATIC_DIR = Path(__file__).resolve().parent / 'static'


def create_app(settings: config.Settings | None = None, *, runner=None,
               turn_timeout: float | None = None, clock=time.time, static_dir: Path | None = None) -> FastAPI:
    """runner：私聊回合的執行者（單一執行者或 {轉接器代號: 執行者}，測試注入用）；
    沒給時，只有設定 fake_turns 才用假轉接器（所有轉接器共用）。
    turn_timeout：只供測試縮短單回合逾時；None 表示用各成員的設定（FR-1）。
    clock：只供測試控制配對碼與 Cookie 的期限、頻率限制的視窗（NFR-3）。
    static_dir：只供測試換掉網頁介面的靜態檔目錄。"""
    settings = settings or config.load()
    static_dir = STATIC_DIR if static_dir is None else Path(static_dir)
    if runner is None and settings.fake_turns:
        runner = FakeRunner()
    if runner is None and settings.bridges:
        runner = bridges.runners(settings.bridges, settings.state_dir)  # NFR-7：接上設定的轉接器橋接

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.db_path = members.prepare_database(settings.state_dir)
        app.state.turns = turns.TurnService(app.state.db_path, runner, timeout=turn_timeout)
        app.state.turns.recover()
        try:
            yield
        finally:
            await app.state.turns.close()

    # 互動式 API 文件頁會從外部 CDN 載入檔案，所以一併關掉。
    app = FastAPI(title='Yiqunren', telemetry=TELEMETRY_OFF, lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    # NFR-3：所有請求先經過 Host、CSRF、配對、大小與頻率檢查。
    app.state.security = security.Security(settings.port, lambda: app.state.db_path, clock)
    app.add_middleware(security.Guard, security=app.state.security)

    @app.get('/api/health')
    def health():
        connection = db.connect(app.state.db_path)
        try:
            version = db.schema_version(connection)
        finally:
            connection.close()
        return {'status': 'ok', 'schema_version': version}

    app.include_router(security.router)
    app.include_router(members.router)
    app.include_router(turns.router)
    # 網頁介面放在最後：上面的 API 路由先比對，其餘路徑才當成靜態檔。
    if (static_dir / 'index.html').is_file():
        app.mount('/', StaticFiles(directory=static_dir, html=True), name='frontend')
    else:
        @app.get('/')
        def frontend_missing():
            return JSONResponse({'detail': '網頁介面還沒打包：請在 frontend/ 執行 npm ci 與 npm run build'},
                                status_code=404)
    return app
