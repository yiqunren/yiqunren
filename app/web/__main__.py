"""啟動後端：python -m app.web（設定見 app/web/config.py）。"""
from __future__ import annotations

import sys

import uvicorn

from app.web import config
from app.web.server import create_app


def main() -> int:
    try:
        settings = config.load()
    except config.ConfigError as exc:
        print('設定錯誤：' + str(exc), file=sys.stderr)
        return 2
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port)
    return 0


if __name__ == '__main__':
    sys.exit(main())
