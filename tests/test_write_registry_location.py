"""寫入權登記庫的預設位置：放在狀態目錄（和後端資料庫同一個目錄），不放在 repo 底下。"""
import os
from pathlib import Path
import stat
import tempfile
import unittest

from app.services.write_ownership import REGISTRY_NAME, OwnershipError, configured_registry
from app.storage import db
from app.web import config


ROOT = Path(__file__).resolve().parents[1]


class RegistryLocationTest(unittest.TestCase):
    def test_default_follows_the_state_directory_not_the_repo(self):
        cases = [
            ({'YIQUNREN_STATE_DIR': '/srv/state-example'}, Path('/srv/state-example') / REGISTRY_NAME),
            ({'XDG_STATE_HOME': '/var/state-example', 'HOME': '/example-home/user'},
             Path('/var/state-example/yiqunren') / REGISTRY_NAME),
            ({'HOME': '/example-home/user'}, Path('/example-home/user/.local/state/yiqunren') / REGISTRY_NAME),
        ]
        for env, expected in cases:
            with self.subTest(env=env):
                path = configured_registry(env).path
                self.assertEqual(path, expected)
                self.assertEqual(path.parent, config.load(env).state_dir)  # 和後端資料庫同一個目錄
                self.assertFalse(path.is_relative_to(ROOT))

    def test_explicit_registry_setting_still_wins(self):
        env = {'YIQUNREN_STATE_DIR': '/srv/state-example', 'YIQUNREN_WRITE_REGISTRY': '/srv/other/registry.sqlite3'}
        self.assertEqual(configured_registry(env).path, Path('/srv/other/registry.sqlite3'))
        self.assertEqual(configured_registry({**env, 'YIQUNREN_WRITE_REGISTRY': ''}).path,
                         Path('/srv/state-example') / REGISTRY_NAME)

    def test_unknown_state_directory_refuses_to_write(self):
        for env in ({}, {'HOME': 'relative-home'}, {'YIQUNREN_STATE_DIR': 'relative/dir'}):
            with self.subTest(env=env), self.assertRaises(OwnershipError):
                configured_registry(env)

    def test_registry_and_backend_database_share_the_state_directory(self):
        for backend_first in (True, False):
            with self.subTest(backend_first=backend_first), tempfile.TemporaryDirectory(
                    prefix='yiqunren-registry-test-') as temporary:
                base = Path(temporary).resolve()  # 登記庫要求路徑不經符號連結
                state = base / 'state'
                project = base / 'project'
                project.mkdir()
                env = {'YIQUNREN_STATE_DIR': str(state)}
                if backend_first:
                    db.prepare(state)
                registry = configured_registry(env)
                lease = registry.claim(str(project.resolve()), ['.'], 'tester')
                db.prepare(state)  # 兩個檔案放在同一個 0700 目錄，後端照常啟動
                self.assertEqual(stat.S_IMODE(os.stat(state).st_mode), 0o700)
                self.assertEqual(stat.S_IMODE(os.stat(state / REGISTRY_NAME).st_mode), 0o600)
                self.assertTrue(db.database_path(state).is_file())
                self.assertEqual([item['lease_id'] for item in configured_registry(env).list()], [lease['lease_id']])


if __name__ == '__main__':
    unittest.main()
