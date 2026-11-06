"""The production-only per-run scratch mount, with mount/umount mocked (the real path is Linux + root)."""

import subprocess
from pathlib import Path

import pytest

from prereg import config, runner


@pytest.fixture
def calls(monkeypatch, tmp_path):
    seen: list[list[str]] = []
    mounted: set[str] = set()

    def fake_run(cmd, **kwargs):
        seen.append(cmd)
        if cmd[0] == "mount":
            mounted.add(cmd[-1])
        if cmd[0] == "umount":
            mounted.discard(cmd[-1])
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(config, "SCRATCH_TMPFS", True)
    monkeypatch.setattr(config, "RUNS_DIR", tmp_path)
    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    monkeypatch.setattr(runner.os.path, "ismount", lambda p: str(p) in mounted)
    return seen


def test_prepare_mounts_a_capped_tmpfs_on_out(calls, tmp_path):
    runner._prepare(tmp_path / "prereg-x", None, {"a.py": b"print(1)"})
    mount = next(c for c in calls if c[0] == "mount")
    options = mount[mount.index("-o") + 1]
    assert mount[-1].endswith("prereg-x/out")
    for opt in (f"size={config.SCRATCH_SIZE}", "nr_inodes=4096", "nosuid", "nodev", "noexec"):
        assert opt in options


def test_destroy_unmounts_before_removing(calls, tmp_path):
    run_dir = tmp_path / "prereg-x"
    runner._prepare(run_dir, None, {"a.py": b"print(1)"})
    runner._destroy(run_dir)
    assert calls[-1][:2] == ["umount", "-l"]
    assert not run_dir.exists()


@pytest.mark.parametrize("failure", ["nonzero", "timeout"])
def test_destroy_survives_umount_failures(monkeypatch, tmp_path, failure, caplog):
    run_dir = tmp_path / "prereg-y"
    (run_dir / "out").mkdir(parents=True)
    monkeypatch.setattr(config, "SCRATCH_TMPFS", True)
    monkeypatch.setattr(runner.os.path, "ismount", lambda p: True)

    def failing(cmd, **kwargs):
        if failure == "timeout":
            raise subprocess.TimeoutExpired(cmd, 10)
        return subprocess.CompletedProcess(cmd, 1, "", "target is busy")

    monkeypatch.setattr(runner.subprocess, "run", failing)
    runner._destroy(run_dir)  # must not raise
    assert not run_dir.exists()
    assert "unmount" in caplog.text


def test_sweep_also_removes_stranded_uploads(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "RUNS_DIR", tmp_path)
    (tmp_path / "prereg-abc").mkdir()
    (tmp_path / "upload-123.csv").write_text("a,b\n1,2\n")
    assert runner.sweep_runs_dir() == 2
    assert list(tmp_path.iterdir()) == []


def test_artifacts_are_chosen_by_name(tmp_path):
    for name in ("c.png", "a.png", "b.png", "d.png"):
        (tmp_path / name).write_bytes(b"\x89PNG")
    assert list(runner._read_artifacts(Path(tmp_path))) == ["a.png", "b.png", "c.png"]
