"""啟動後端：python -m app.web（設定見 app/web/config.py）。

python -m app.web pair    產生一組一次性配對碼（NFR-3），伺服器有沒有在跑都可以
python -m app.web unpair  撤銷所有已配對的瀏覽器，尚未使用的配對碼也作廢
"""
from __future__ import annotations

import sys

import uvicorn

from app.storage import db
from app.web import config, members, security
from app.web.server import create_app


USAGE = '用法：python -m app.web [pair | unpair]'


def main(argv=None, env=None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    command = argv[0] if argv else None
    if len(argv) > 1 or command not in (None, 'pair', 'unpair'):
        print(USAGE, file=sys.stderr)
        return 2
    try:
        settings = config.load(env)
        db_path = members.prepare_database(settings.state_dir)
    except config.ConfigError as exc:
        print('設定錯誤：' + str(exc), file=sys.stderr)
        return 2
    except db.StorageError as exc:
        print('狀態資料庫錯誤：' + str(exc), file=sys.stderr)
        return 2
    if command == 'pair':
        # 配對碼只印在這個指令的輸出，伺服器自己的輸出與 log 不會出現。
        print('配對碼：' + security.issue_code(db_path))
        print('10 分鐘內有效，只能用一次；再產生新的配對碼，這組就作廢。')
        return 0
    if command == 'unpair':
        count = security.revoke_all(db_path)
        print('已撤銷 %d 個已配對的瀏覽器，尚未使用的配對碼也已作廢。' % count)
        return 0
    try:
        app = create_app(settings)  # 接上轉接器時也會檢查設定（例如 Claude（API）需要 ANTHROPIC_API_KEY）
    except config.ConfigError as exc:
        print('設定錯誤：' + str(exc), file=sys.stderr)
        return 2
    if not security.has_sessions(db_path):
        print('還沒有配對任何瀏覽器：另開終端執行 python -m app.web pair 取得配對碼。', file=sys.stderr)
    uvicorn.run(app, host=settings.host, port=settings.port)
    return 0


if __name__ == '__main__':
    sys.exit(main())
