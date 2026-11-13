"""FastAPI app。只裝 fastapi＋uvicorn，並在建立 app 時明確關閉內建遙測（NFR-4）。"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.storage import db
from app.web import config


# 程式裡明確給的值會蓋過 FASTAPI_OTEL_AUTO_CONFIGURE 等環境變數，使用者環境怎麼設都不外送。
TELEMETRY_OFF = {'auto_configure': False, 'tracing': False, 'metrics': False, 'logs': False}


def create_app(settings: config.Settings | None = None) -> FastAPI:
    settings = settings or config.load()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.db_path = db.prepare(settings.state_dir)
        yield

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

    return app
