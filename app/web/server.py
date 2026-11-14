"""FastAPI app。只裝 fastapi＋uvicorn，並在建立 app 時明確關閉內建遙測（NFR-4）。"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.storage import db
from app.web import config, members, turns
from app.web.fake_runner import FakeRunner


# 程式裡明確給的值會蓋過 FASTAPI_OTEL_AUTO_CONFIGURE 等環境變數，使用者環境怎麼設都不外送。
TELEMETRY_OFF = {'auto_configure': False, 'tracing': False, 'metrics': False, 'logs': False}


def create_app(settings: config.Settings | None = None, *, runner=None,
               turn_timeout: float | None = None) -> FastAPI:
    """runner：私聊回合的執行者（單一執行者或 {轉接器代號: 執行者}，測試注入用）；
    沒給時，只有設定 fake_turns 才用假轉接器（所有轉接器共用）。
    turn_timeout：只供測試縮短單回合逾時；None 表示用各成員的設定（FR-1）。"""
    settings = settings or config.load()
    if runner is None and settings.fake_turns:
        runner = FakeRunner()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.db_path = db.prepare(settings.state_dir)
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

    @app.get('/api/health')
    def health():
        connection = db.connect(app.state.db_path)
        try:
            version = db.schema_version(connection)
        finally:
            connection.close()
        return {'status': 'ok', 'schema_version': version}

    app.include_router(members.router)
    app.include_router(turns.router)
    return app
