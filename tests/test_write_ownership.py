"""共用寫入權的離線驗收；只使用臨時目錄及假工作者。"""
import asyncio
import json
import multiprocessing
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from app.services.write_ownership import OwnershipError, WriteRegistry, guarded_write


def race_claim(database, project, start, results):
    start.wait(5)
    try:
        WriteRegistry(database).claim(project, ['same.txt'], str(os.getpid()))
        results.put('claimed')
    except OwnershipError:
        results.put('blocked')


class OwnershipTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='office-write-test-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.project = self.root / 'project'
        self.project.mkdir()
        self.path = self.root / 'registry.sqlite3'
        self.now = 1000.0
        self.registry = WriteRegistry(self.path, clock=lambda: self.now)

    def claim(self, files, holder='first', ttl=10):
        return self.registry.claim(str(self.project), files, holder, ttl)

    def test_exact_and_directory_scopes_block_overlap_but_allow_other_files(self):
        self.claim(['src/'])
        self.claim(['docs/a.md'], 'second')
        for files in (['src/a.py'], ['src/'], ['.']):
            with self.subTest(files=files), self.assertRaises(OwnershipError):
                self.claim(files, 'third')
        self.claim(['src2/a.py'], 'fourth')

    def test_nested_projects_cannot_bypass_the_scope(self):
        child = self.project / 'child'
        child.mkdir()
        self.claim(['child/'])
        with self.assertRaises(OwnershipError):
            self.registry.claim(str(child), ['a.txt'], 'nested')

    def test_expiry_is_unknown_and_never_automatically_reassigned(self):
        lease = self.claim(['a.txt'])
        self.now += 11
        self.assertEqual(self.registry.list()[0]['state'], 'unknown')
        for action in ('renew', 'release'):
            with self.subTest(action=action), self.assertRaises(OwnershipError):
                self.registry.change(lease['lease_id'], 'first', action)
        with self.assertRaises(OwnershipError):
            self.claim(['a.txt'], 'second')
        with self.assertRaises(OwnershipError):
            self.registry.change(lease['lease_id'], 'first', 'resolve')
        self.registry.change(lease['lease_id'], 'first', 'resolve', stopped=True)
        self.claim(['a.txt'], 'second')

    def test_owner_and_old_lease_cannot_release_a_new_holder(self):
        old = self.claim(['a.txt'])
        with self.assertRaises(OwnershipError):
            self.registry.change(old['lease_id'], 'other', 'release')
        self.registry.change(old['lease_id'], 'first', 'release')
        self.claim(['a.txt'], 'second')
        with self.assertRaises(OwnershipError):
            self.registry.change(old['lease_id'], 'first', 'release')
        self.assertEqual(self.registry.list()[0]['holder'], 'second')

    def test_renewal_and_clock_rollback(self):
        lease = self.claim(['a.txt'])
        self.now += 5
        renewed = self.registry.change(lease['lease_id'], 'first', 'renew', ttl=20)
        self.assertEqual(renewed['expires_at'], 1025)
        self.now = 1004
        self.assertEqual(self.registry.list()[0]['state'], 'unknown')

    def test_invalid_paths_and_redirects(self):
        outside = self.root / 'outside'
        outside.mkdir()
        (self.project / 'link').symlink_to(outside, target_is_directory=True)
        for files in (['../outside/a'], ['/tmp/a'], ['*.py'], ['link/a'], []):
            with self.subTest(files=files), self.assertRaises(OwnershipError):
                self.claim(files)

    def test_corrupt_database_and_unknown_record_state_block_claims(self):
        lease = self.claim(['a.txt'])
        with sqlite3.connect(self.path) as db:
            db.execute('UPDATE leases SET state=? WHERE id=?', ('unrecognised', lease['lease_id']))
        with self.assertRaises(OwnershipError):
            self.claim(['other.txt'], 'second')
        corrupt = self.root / 'corrupt.sqlite3'
        corrupt.write_text('not a database')
        corrupt.chmod(0o600)
        with self.assertRaises(OwnershipError):
            WriteRegistry(corrupt).claim(str(self.project), ['.'], 'second')

    def test_independent_processes_have_exactly_one_winner(self):
        context = multiprocessing.get_context('spawn')
        start, results = context.Event(), context.Queue()
        children = [context.Process(target=race_claim, args=(str(self.path), str(self.project), start, results)) for _ in range(2)]
        try:
            for child in children: child.start()
            start.set()
            answers = [results.get(timeout=10) for _ in children]
            self.assertCountEqual(answers, ['claimed', 'blocked'])
            for child in children:
                child.join(5)
                self.assertEqual(child.exitcode, 0)
        finally:
            for child in children:
                if child.is_alive():
                    child.terminate()
                    child.join(5)
            results.close()
            results.join_thread()

    def test_cli_records_and_conflict_exit_status(self):
        env = {**os.environ, 'AIOFFICE_WRITE_REGISTRY': str(self.path)}
        command = [sys.executable, '-B', 'scripts/write_ownership.py']
        args = ['claim', '--project', str(self.project), '--files', 'a.txt', '--holder', 'cli', '--ttl', '20']
        first = subprocess.run(command + args, capture_output=True, text=True, env=env)
        second = subprocess.run(command + args, capture_output=True, text=True, env=env)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 1)
        record = json.loads(first.stdout)['data']
        self.assertEqual(record['holder'], 'cli')
        self.assertEqual(record['expires_at']-record['acquired_at'], 20)


class GuardTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='office-write-guard-')
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name) / 'project'
        self.project.mkdir()
        self.registry = WriteRegistry(Path(self.temporary.name) / 'registry.sqlite3')
        self.patch = patch('app.services.write_ownership.configured_registry', return_value=self.registry)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    async def test_second_operation_never_starts_and_success_releases(self):
        started, finish = asyncio.Event(), asyncio.Event()
        async def first():
            started.set()
            await finish.wait()
            return 'done'
        task = asyncio.create_task(guarded_write(self.project, 'office', first))
        await started.wait()
        invoked = False
        async def second():
            nonlocal invoked
            invoked = True
        try:
            with self.assertRaises(OwnershipError):
                await guarded_write(self.project, 'other', second)
            self.assertFalse(invoked)
        finally:
            finish.set()
            await task
        self.assertEqual(self.registry.list(), [])

    async def test_failure_cancellation_and_restart_remain_blocked(self):
        async def failed():
            raise RuntimeError('fake failure')
        with self.assertRaises(RuntimeError):
            await guarded_write(self.project, 'office', failed)
        self.assertEqual(WriteRegistry(self.registry.path).list()[0]['state'], 'unknown')
        with self.assertRaises(OwnershipError):
            await guarded_write(self.project, 'office', failed)
        lease = self.registry.list()[0]
        self.registry.change(lease['lease_id'], 'office', 'resolve', stopped=True)
        entered = asyncio.Event()
        async def running():
            entered.set()
            await asyncio.Event().wait()
        task = asyncio.create_task(guarded_write(self.project, 'office', running))
        await entered.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(self.registry.list()[0]['state'], 'unknown')


if __name__ == '__main__':
    unittest.main()
