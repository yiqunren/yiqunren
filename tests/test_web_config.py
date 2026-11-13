"""後端設定的離線驗收（NFR-3 預設只聽本機、NFR-4 路徑可由環境變數指定）。"""
from pathlib import Path
import unittest

from app.web.config import DEFAULT_PORT, ConfigError, load


HOME = {'HOME': '/example-home/user'}


class ConfigTest(unittest.TestCase):
    def test_defaults_listen_on_localhost_only(self):
        settings = load(dict(HOME))
        self.assertEqual(settings.host, '127.0.0.1')
        self.assertEqual(settings.port, DEFAULT_PORT)
        self.assertNotIn(settings.port, (8001, 8101))
        self.assertEqual(settings.state_dir, Path('/example-home/user/.local/state/yiqunren'))

    def test_xdg_state_home_is_used_when_absolute(self):
        settings = load({**HOME, 'XDG_STATE_HOME': '/var/state-example'})
        self.assertEqual(settings.state_dir, Path('/var/state-example/yiqunren'))

    def test_relative_xdg_state_home_is_ignored(self):
        settings = load({**HOME, 'XDG_STATE_HOME': 'relative/state'})
        self.assertEqual(settings.state_dir, Path('/example-home/user/.local/state/yiqunren'))

    def test_overrides(self):
        settings = load({**HOME, 'YIQUNREN_HOST': '0.0.0.0', 'YIQUNREN_PORT': '9123',
                         'YIQUNREN_STATE_DIR': '/srv/yiqunren-state'})
        self.assertEqual((settings.host, settings.port, settings.state_dir),
                         ('0.0.0.0', 9123, Path('/srv/yiqunren-state')))

    def test_invalid_values_are_rejected(self):
        for env in ({'YIQUNREN_HOST': 'localhost'}, {'YIQUNREN_HOST': ''},
                    {'YIQUNREN_PORT': '0'}, {'YIQUNREN_PORT': '65536'}, {'YIQUNREN_PORT': '80a'},
                    {'YIQUNREN_PORT': '８０'}, {'YIQUNREN_PORT': '-1'},
                    {'YIQUNREN_STATE_DIR': 'relative/dir'}):
            with self.subTest(env=env), self.assertRaises(ConfigError):
                load({**HOME, **env})

    def test_missing_home_requires_explicit_state_dir(self):
        with self.assertRaises(ConfigError):
            load({})
        self.assertEqual(load({'YIQUNREN_STATE_DIR': '/srv/s'}).state_dir, Path('/srv/s'))


if __name__ == '__main__':
    unittest.main()
