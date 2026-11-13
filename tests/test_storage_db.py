"""狀態資料庫的離線驗收：WAL、版本管理、目錄與檔案權限；只使用臨時目錄。"""
import os
from pathlib import Path
import stat
import tempfile
import unittest

from app.storage import db


class DatabaseTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='yiqunren-db-test-')
        self.addCleanup(self.temporary.cleanup)
        self.state = Path(self.temporary.name) / 'state'

    def test_prepare_creates_private_wal_database_at_latest_version(self):
        path = db.prepare(self.state)
        self.assertEqual(path, self.state / db.DB_NAME)
        self.assertEqual(stat.S_IMODE(os.stat(self.state).st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
        connection = db.connect(path)
        self.addCleanup(connection.close)
        self.assertEqual(connection.execute('PRAGMA journal_mode').fetchone()[0], 'wal')
        self.assertEqual(db.schema_version(connection), db.SCHEMA_VERSION)
        columns = {row['name'] for row in connection.execute('PRAGMA table_info(requests)')}
        self.assertEqual(columns, {'id', 'kind', 'payload_hash', 'state', 'created', 'updated', 'result'})

    def test_prepare_twice_keeps_data(self):
        path = db.prepare(self.state)
        connection = db.connect(path)
        connection.execute("INSERT INTO requests VALUES ('x', 'k', 'h', 'claimed', 1, 1, NULL)")
        connection.close()
        db.prepare(self.state)
        connection = db.connect(path)
        self.addCleanup(connection.close)
        self.assertEqual(connection.execute('SELECT COUNT(*) FROM requests').fetchone()[0], 1)

    def test_version_1_database_is_upgraded_and_keeps_data(self):
        self.state.mkdir(mode=0o700)
        path = self.state / db.DB_NAME
        path.touch(mode=0o600)
        connection = db.connect(path)
        for statement in db.MIGRATIONS[0]:
            connection.execute(statement)
        connection.execute('PRAGMA user_version = 1')
        connection.execute("INSERT INTO requests VALUES ('x', 'k', 'h', 'claimed', 1, 1, NULL)")
        connection.close()
        db.prepare(self.state)
        connection = db.connect(path)
        self.addCleanup(connection.close)
        self.assertEqual(db.schema_version(connection), db.SCHEMA_VERSION)
        self.assertEqual(connection.execute('SELECT COUNT(*) FROM requests').fetchone()[0], 1)
        tables = {row['name'] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({'requests', 'turns', 'turn_events'} <= tables)

    def test_newer_database_is_refused(self):
        path = db.prepare(self.state)
        connection = db.connect(path)
        connection.execute('PRAGMA user_version = %d' % (db.SCHEMA_VERSION + 1))
        connection.close()
        with self.assertRaisesRegex(db.StorageError, '比程式新'):
            db.prepare(self.state)

    def test_shared_directory_is_refused(self):
        self.state.mkdir(mode=0o755)
        os.chmod(self.state, 0o755)
        with self.assertRaises(db.StorageError):
            db.prepare(self.state)

    def test_symlinked_database_file_is_refused(self):
        self.state.mkdir(mode=0o700)
        target = Path(self.temporary.name) / 'elsewhere.sqlite3'
        target.touch(mode=0o600)
        (self.state / db.DB_NAME).symlink_to(target)
        with self.assertRaises(db.StorageError):
            db.prepare(self.state)

    def test_relative_state_dir_is_refused(self):
        with self.assertRaises(db.StorageError):
            db.prepare(Path('relative/state'))


if __name__ == '__main__':
    unittest.main()
