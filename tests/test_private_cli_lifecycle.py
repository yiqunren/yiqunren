"""以自有假 CLI 核對私聊取消；不啟動真實模型或讀取認證。"""
import asyncio
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import discussion_host, private_cli
from scripts.discussion_host import process_stat


class ControlledProcess:
    """只用事件模擬停止狀態；不建立真實程序。"""
    def __init__(self, mode='normal'):
        self.pid = 444
        self.returncode = None
        self.mode = mode
        self.started, self.terminating, self.exited = (asyncio.Event() for _ in range(3))
        self.terminate_count = self.kill_count = 0

    async def communicate(self, message):
        self.started.set()
        await asyncio.Event().wait()

    def terminate(self):
        self.terminate_count += 1
        self.terminating.set()
        if self.mode == 'normal':
            self.returncode = -15
            self.exited.set()

    def kill(self):
        self.kill_count += 1
        if self.mode != 'stubborn':
            self.returncode = -9
            self.exited.set()

    async def wait(self):
        await self.exited.wait()
        return self.returncode


def fake_identity(monkeypatch, process):
    """事件模擬只測有界等待；程序群組歸屬由上方真實假 CLI 測試核對。"""
    monkeypatch.setattr(private_cli, 'birth_receipt', lambda pid: {'pgid': pid})
    monkeypatch.setattr(private_cli, 'group_ended', lambda receipt: process.returncode is not None)
    monkeypatch.setattr(private_cli, '_communicate_bounded',
                        lambda owned, message, tasks: owned.communicate(message))
    def signal_fake(pid, selected):
        assert pid == process.pid
        (process.terminate if selected == signal.SIGTERM else process.kill)()
    monkeypatch.setattr(private_cli.os, 'killpg', signal_fake)


@pytest.mark.parametrize('mode,kill_count', [('normal', 0), ('term-ignored', 1)])
def test_timeout_waits_for_owned_process_exit(monkeypatch, mode, kill_count):
    monkeypatch.setattr(private_cli, 'TERMINATE_GRACE', .01)
    async def check():
        process = ControlledProcess(mode)
        fake_identity(monkeypatch, process)
        with pytest.raises(asyncio.TimeoutError):
            await private_cli.communicate_private(process, b'synthetic', .01)
        assert process.returncode is not None
        assert process.terminate_count == 1 and process.kill_count == kill_count
        assert len(asyncio.all_tasks()) == 1
    asyncio.run(check())


def test_repeated_cancel_does_not_abandon_cleanup(monkeypatch):
    monkeypatch.setattr(private_cli, 'TERMINATE_GRACE', 1)
    async def check():
        process = ControlledProcess('delayed')
        fake_identity(monkeypatch, process)
        task = asyncio.create_task(private_cli.communicate_private(process, b'synthetic', 30))
        await process.started.wait()
        task.cancel()
        await process.terminating.wait()
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done()
        process.returncode = -15
        process.exited.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert process.terminate_count == 1 and process.kill_count == 0
        assert len(asyncio.all_tasks()) == 1
    asyncio.run(check())


def test_unconfirmed_exit_reports_unknown_and_finishes_cleanup_task(monkeypatch):
    monkeypatch.setattr(private_cli, 'TERMINATE_GRACE', .01)
    async def check():
        process = ControlledProcess('stubborn')
        fake_identity(monkeypatch, process)
        with pytest.raises(RuntimeError, match='停止狀態未知'):
            await private_cli.communicate_private(process, b'synthetic', .01)
        assert process.returncode is None
        assert process.terminate_count == 1 and process.kill_count == 1
        assert len(asyncio.all_tasks()) == 1
    asyncio.run(check())


@pytest.mark.parametrize('stream', [1, 2])
@pytest.mark.parametrize('size', [0, 2_000_000, 2_000_001])
def test_private_output_is_bounded_while_reading_and_reaps_process(stream, size):
    async def check():
        script = ('import os,sys,time\nsys.stdin.read()\n'
                  f'data=b"x"*{size}\n'
                  f'while data:\n n=os.write({stream},data);data=data[n:]\n'
                  + ('time.sleep(30)\n' if size > 2_000_000 else ''))
        process = await asyncio.create_subprocess_exec(
            sys.executable, '-c', script, stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            env={'PATH': '/usr/bin:/bin'}, start_new_session=True)
        try:
            if size > 2_000_000:
                with pytest.raises(RuntimeError, match='輸出超過 2 MB'):
                    await private_cli.communicate_private(process, b'synthetic', 5)
            else:
                stdout, stderr = await private_cli.communicate_private(process, b'synthetic', 5)
                assert stdout == (b'x' * size if stream == 1 else b'')
                assert stderr == b''
            assert process.returncode is not None
            assert len(asyncio.all_tasks()) == 1
        finally:
            if process.returncode is None:
                process.terminate()
                await asyncio.wait_for(process.wait(), 5)
    asyncio.run(check())


def zombie_stat(pid):
    """非 root 執行時，殭屍程序的 /proc 擁有者會變成 root，所以 uid 和目前使用者不同。"""
    return {'pid': pid, 'state': 'Z', 'pgid': pid, 'sid': pid, 'start_ticks': 1, 'uid': os.getuid() + 1}


def test_birth_receipt_treats_real_zombie_leader_as_gone():
    process = subprocess.Popen([sys.executable, '-c', ''], start_new_session=True)
    try:
        deadline = time.monotonic() + 10
        while process_stat(process.pid)['state'] != 'Z':
            assert time.monotonic() < deadline
            time.sleep(.01)
        with pytest.raises(ProcessLookupError):
            discussion_host.birth_receipt(process.pid)
    finally:
        process.wait()


def test_signal_skips_zombie_leader_without_raising(monkeypatch):
    def unexpected(pid, selected):
        raise AssertionError('殭屍領頭程序不應再送訊號')
    monkeypatch.setattr(discussion_host, 'process_stat', zombie_stat)
    monkeypatch.setattr(private_cli.os, 'killpg', unexpected)
    private_cli._signal_process(SimpleNamespace(pid=4242, returncode=None), {'pgid': 4242}, signal.SIGTERM)


def test_call_survives_zombie_leader_when_reading_receipt(monkeypatch):
    async def bounded(owned, message, tasks):
        return b'out', b''
    async def finished():
        return 0
    def group_gone(pid, selected):
        raise ProcessLookupError
    monkeypatch.setattr(discussion_host, 'process_stat', zombie_stat)
    monkeypatch.setattr(private_cli, '_communicate_bounded', bounded)
    monkeypatch.setattr(private_cli.os, 'killpg', group_gone)
    process = SimpleNamespace(pid=4242, returncode=0, wait=finished)
    assert asyncio.run(private_cli.communicate_private(process, b'', 1)) == (b'out', b'')
