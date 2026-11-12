"""工作區指紋（scripts/workspace_fingerprint.py）：只用暫存目錄，不碰真實工作區。"""
import os

import pytest

from scripts import workspace_fingerprint as fp


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path / "workspace"
    (root / "sub").mkdir(parents=True)
    (root / "a.txt").write_text("alpha")
    (root / "sub" / "b.txt").write_text("beta")
    return root


def test_unchanged_workspace_has_the_same_fingerprint(workspace):
    first, second = fp.take(workspace), fp.take(workspace)
    assert first is not None and first == second
    assert set(first) == {"a.txt", "sub", "sub/b.txt"}
    assert fp.diff(first, second) == ([], 0)


def test_content_change_with_the_same_size_and_mtime_is_detected(workspace):
    target = workspace / "sub" / "b.txt"
    before = fp.take(workspace)
    info = target.stat()
    target.write_text("BETA")
    os.utime(target, ns=(info.st_atime_ns, info.st_mtime_ns))
    after = fp.take(workspace)
    assert after["sub/b.txt"][2:4] == before["sub/b.txt"][2:4]
    assert fp.diff(before, after) == (["sub/b.txt"], 1)


def test_added_removed_and_mode_changes_are_listed(workspace):
    before = fp.take(workspace)
    (workspace / "a.txt").chmod(0o600 if (workspace / "a.txt").stat().st_mode & 0o044 else 0o644)
    (workspace / "sub" / "b.txt").unlink()
    (workspace / "new.txt").write_text("n")
    changed, total = fp.diff(before, fp.take(workspace))
    assert "a.txt" in changed and "sub/b.txt" in changed and "new.txt" in changed
    assert total == len(changed)


def test_symlinks_are_recorded_but_never_followed(workspace, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("not walked")
    (workspace / "link").symlink_to(outside)
    before = fp.take(workspace)
    assert before["link"][0] == "link" and before["link"][5] == str(outside)
    assert not any(path.startswith("link/") for path in before)
    # 連結外的內容變動不算工作區變動；改連結目標才算。
    (outside / "secret.txt").write_text("changed outside")
    assert fp.diff(before, fp.take(workspace)) == ([], 0)
    (workspace / "link").unlink()
    (workspace / "link").symlink_to(tmp_path)
    assert fp.diff(before, fp.take(workspace)) == (["link"], 1)


def test_over_the_entry_limit_cannot_prove_anything(workspace, monkeypatch):
    monkeypatch.setattr(fp, "MAX_ENTRIES", 2)
    assert fp.take(workspace) is None


def test_over_the_byte_limit_cannot_prove_anything(workspace, monkeypatch):
    monkeypatch.setattr(fp, "MAX_BYTES", 8)
    assert fp.take(workspace) is None


def test_missing_workspace_cannot_prove_anything(tmp_path):
    assert fp.take(tmp_path / "missing") is None


def test_unreadable_entries_cannot_prove_anything(workspace):
    if os.geteuid() == 0:
        pytest.skip("root 讀得到 0 權限的檔")
    target = workspace / "sub" / "b.txt"
    target.chmod(0)
    try:
        assert fp.take(workspace) is None
    finally:
        target.chmod(0o600)


def test_fifo_is_recorded_without_being_opened(workspace):
    os.mkfifo(workspace / "pipe")
    before = fp.take(workspace)
    assert before["pipe"][0] == "other" and before["pipe"][5] is None


def test_changed_list_is_capped(workspace, monkeypatch):
    monkeypatch.setattr(fp, "CHANGED_LIMIT", 2)
    before = fp.take(workspace)
    for index in range(5):
        (workspace / f"n{index}.txt").write_text("x")
    changed, total = fp.diff(before, fp.take(workspace))
    assert changed == ["n0.txt", "n1.txt"] and total == 5
