"""每段對話工作目錄（app/storage/workspaces.py，SPEC NFR-7）的離線驗收；只使用臨時目錄。"""
import os
from pathlib import Path
import shutil
import stat
import tempfile
import unittest
import uuid

from app.storage import workspaces


class WorkspaceTest(unittest.TestCase):
    def setUp(self):
        directory = Path(tempfile.mkdtemp(prefix='yq-ws-'))
        self.addCleanup(shutil.rmtree, directory, True)
        self.state = directory / 'state'
        self.state.mkdir(mode=0o700)
        self.root = workspaces.root(self.state)
        self.conversation = str(uuid.uuid4())
        self.workspace = workspaces.path(self.state, self.conversation)

    def test_path_is_one_level_under_root_and_requires_uuid(self):
        self.assertEqual(self.workspace, self.state / 'workspaces' / self.conversation)
        self.assertEqual(workspaces.path(self.state, self.conversation.upper()), self.workspace)
        for bad in ('../x', 'not-a-uuid', ''):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                workspaces.path(self.state, bad)

    def test_ensure_creates_private_directories_and_is_idempotent(self):
        self.assertEqual(workspaces.ensure(str(self.workspace), self.root), self.workspace)
        for directory in (self.root, self.workspace):
            self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o700)
        (self.workspace / 'kept.md').write_text('x')
        self.assertEqual(workspaces.ensure(str(self.workspace), self.root), self.workspace)
        self.assertTrue((self.workspace / 'kept.md').exists())

    def test_ensure_refuses_paths_outside_root(self):
        for bad in (str(self.state / self.conversation), str(self.root / 'a' / self.conversation),
                    'workspaces/' + self.conversation, None):
            with self.subTest(bad=bad), self.assertRaises(workspaces.WorkspaceError):
                workspaces.ensure(bad, self.root)
        self.assertFalse(self.root.exists())

    def test_check_refuses_unsafe_directories(self):
        workspaces.ensure(str(self.workspace), self.root)
        self.assertEqual(workspaces.check(str(self.workspace), self.root), self.workspace)
        outside = Path(tempfile.mkdtemp(prefix='yq-ws-out-'))
        self.addCleanup(shutil.rmtree, outside, True)
        outside.chmod(0o700)
        link = self.root / str(uuid.uuid4())
        link.symlink_to(outside)
        upper = self.root / str(uuid.uuid4()).upper()
        upper.mkdir(mode=0o700)
        shared = self.root / str(uuid.uuid4())
        shared.mkdir()
        shared.chmod(0o755)
        plain = self.root / str(uuid.uuid4())
        plain.write_text('x')
        cases = {'missing': str(self.root / str(uuid.uuid4())), 'symlink': str(link),
                 'non-canonical name': str(upper), 'shared mode': str(shared), 'regular file': str(plain),
                 'not uuid': str(self.root / 'notes'), 'relative': 'workspaces/' + self.conversation, 'empty': ''}
        for name, value in cases.items():
            with self.subTest(name), self.assertRaises(workspaces.WorkspaceError):
                workspaces.check(value, self.root)

    def test_check_refuses_shared_root(self):
        workspaces.ensure(str(self.workspace), self.root)
        self.root.chmod(0o755)
        with self.assertRaises(workspaces.WorkspaceError):
            workspaces.check(str(self.workspace), self.root)

    def test_remove_deletes_tree_without_following_links(self):
        self.assertFalse(workspaces.remove(self.state, self.conversation))
        workspaces.ensure(str(self.workspace), self.root)
        outside = Path(tempfile.mkdtemp(prefix='yq-ws-out-'))
        self.addCleanup(shutil.rmtree, outside, True)
        (outside / 'keep.md').write_text('x')
        (self.workspace / 'sub').mkdir()
        (self.workspace / 'sub' / 'note.md').write_text('x')
        os.symlink(outside, self.workspace / 'link')
        self.assertTrue(workspaces.remove(self.state, self.conversation))
        self.assertFalse(self.workspace.exists())
        self.assertTrue((outside / 'keep.md').exists())

    def test_remove_unlinks_symlink_itself(self):
        outside = Path(tempfile.mkdtemp(prefix='yq-ws-out-'))
        self.addCleanup(shutil.rmtree, outside, True)
        (outside / 'keep.md').write_text('x')
        self.root.mkdir(mode=0o700)
        self.workspace.symlink_to(outside)
        self.assertTrue(workspaces.remove(self.state, self.conversation))
        self.assertFalse(self.workspace.is_symlink())
        self.assertTrue((outside / 'keep.md').exists())


if __name__ == '__main__':
    unittest.main()
