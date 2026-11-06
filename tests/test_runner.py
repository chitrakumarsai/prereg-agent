import pytest
import time
from pathlib import Path

from conftest import SANDBOX

from prereg import config
from prereg.runner import _classify, build_command, run_in_sandbox


def _cmd() -> list[str]:
    return build_command("n", Path("/r/data"), Path("/r/code"), Path("/r/out"), "a.py", 30)


def _flag(cmd: list[str], name: str) -> str:
    return cmd[cmd.index(name) + 1]


def test_command_carries_every_containment_control():
    cmd = _cmd()
    assert _flag(cmd, "--network") == "none"
    assert _flag(cmd, "--runtime") == config.SANDBOX_RUNTIME
    assert _flag(cmd, "--memory") == _flag(cmd, "--memory-swap") == config.MEMORY_LIMIT
    assert _flag(cmd, "--pids-limit") == str(config.PIDS_LIMIT)
    assert _flag(cmd, "--cap-drop") == "ALL"
    assert _flag(cmd, "--user") == config.SANDBOX_UID
    assert {"--rm", "--read-only"} <= set(cmd)
    assert "/r/data:/data:ro" in cmd and "/r/code:/code:ro" in cmd


def test_command_starts_the_process_with_an_empty_environment():
    cmd = _cmd()
    env_at = cmd.index("env")
    assert cmd[env_at + 1] == "-i"
    assert tuple(cmd[env_at + 2 : env_at + 2 + len(config.SANDBOX_ENV)]) == config.SANDBOX_ENV
    assert "-e" not in cmd and "--env" not in cmd and "--env-file" not in cmd


def test_classify_exit_codes():
    assert _classify(0, 1.0, 30) == "ok"
    assert _classify(124, 30.1, 30) == "timeout"
    assert _classify(137, 2.0, 30) == "killed"
    assert _classify(1, 2.0, 30) == "error"


@SANDBOX
def test_sandbox_has_no_secrets_and_no_network(demo_csv, monkeypatch):
    monkeypatch.setenv("VULTR_INFERENCE_KEY", "should-never-leak")
    code = b"""
import os, json, socket
print(sorted(os.environ))
try:
    socket.create_connection(("1.1.1.1", 80), timeout=3); net = "open"
except OSError as e:
    net = type(e).__name__
json.dump({"env": dict(os.environ), "net": net}, open("/out/result.json", "w"))
"""
    run = run_in_sandbox(demo_csv, {"a.py": code}, "a.py")
    assert run.status == "ok", run.log
    assert "VULTR_INFERENCE_KEY" not in run.result["env"]
    # LC_CTYPE is set by CPython's own locale coercion inside the process, not passed in.
    assert set(run.result["env"]) <= {"PATH", "HOME", "MPLCONFIGDIR", "LC_CTYPE"}
    assert run.result["net"] != "open"


@SANDBOX
def test_sandbox_data_is_read_only(demo_csv):
    code = b"open('/data/input.csv', 'a').write('x')"
    run = run_in_sandbox(demo_csv, {"a.py": code}, "a.py")
    assert run.status == "error"
    assert "Read-only file system" in run.log or "Permission denied" in run.log


@SANDBOX
def test_infinite_loop_is_killed_at_the_timeout(demo_csv):
    started = time.monotonic()
    run = run_in_sandbox(demo_csv, {"a.py": b"while True:\n    pass\n"}, "a.py", timeout_s=3)
    assert run.status == "timeout"
    assert time.monotonic() - started < 20


@SANDBOX
def test_run_folder_is_destroyed(demo_csv, monkeypatch, tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    monkeypatch.setattr(config, "RUNS_DIR", runs)  # private dir: other tests' background runs can't interfere
    run_in_sandbox(demo_csv, {"a.py": b"print('hi')"}, "a.py")
    assert not any(runs.glob("prereg-*"))


@SANDBOX
def test_symlinked_result_is_refused(demo_csv, tmp_path):
    secret = tmp_path / "host-secret.json"
    secret.write_text('{"stolen": true}')
    code = f"import os; os.symlink({str(secret)!r}, '/out/result.json')".encode()
    run = run_in_sandbox(demo_csv, {"a.py": code}, "a.py")
    assert run.result is None
    assert "symlinks are refused" in run.result_error


@SANDBOX
def test_long_line_and_line_flood_are_capped(demo_csv):
    code = b"import sys\nsys.stdout.write('A' * 3_000_000)\nprint()\nprint('\\n' * 200_000)\n"
    run = run_in_sandbox(demo_csv, {"a.py": code}, "a.py")
    assert run.log_truncated
    assert len(run.log) <= config.MAX_LOG_BYTES
    assert run.log.count("\n") < 2_000


@SANDBOX
def test_pid1_environment_is_empty_too(demo_csv):
    code = b"print(sorted(v.split('=')[0] for v in open('/proc/1/environ').read().split('\\0') if v))"
    run = run_in_sandbox(demo_csv, {"a.py": code}, "a.py")
    assert run.status == "ok", run.log
    assert run.log.strip() == str(sorted(["PATH", "HOME", "MPLCONFIGDIR"]))


@SANDBOX
def test_fork_bomb_hits_the_pids_limit(demo_csv):
    code = b"""
import os, time
n = 0
try:
    for _ in range(1000):
        if os.fork() == 0:
            time.sleep(10); os._exit(0)
        n += 1
    print("UNBOUNDED", n)
except OSError:
    print("CAPPED", n)
"""
    run = run_in_sandbox(demo_csv, {"a.py": code}, "a.py", timeout_s=8)
    # Under gVisor the pids cap ends the whole sandbox within a second; under runc fork() fails instead.
    assert "UNBOUNDED" not in run.log, run.log
    assert run.status != "ok" or "CAPPED" in run.log
    assert run.duration_s < 8


@SANDBOX
def test_fifo_in_out_does_not_hang_the_host(demo_csv):
    code = b"import os\nos.mkfifo('/out/result.json')\nos.mkfifo('/out/chart.png')\n"
    started = time.monotonic()
    run = run_in_sandbox(demo_csv, {"a.py": code}, "a.py")
    assert time.monotonic() - started < 15
    assert run.result is None and run.artifacts == {}


@pytest.mark.parametrize("payload", ["9" * 5000, "[" * 100_000 + "]" * 100_000])
def test_hostile_result_json_is_reported_not_raised(tmp_path, payload):
    from prereg.runner import _read_result
    (tmp_path / "result.json").write_text(payload)
    result, error = _read_result(tmp_path)
    assert result is None and error


def test_startup_sweep_removes_leftover_run_folders(tmp_path, monkeypatch):
    from prereg.runner import sweep_runs_dir
    monkeypatch.setattr(config, "RUNS_DIR", tmp_path)
    (tmp_path / "prereg-abc" / "out").mkdir(parents=True)
    (tmp_path / "unrelated").mkdir()
    assert sweep_runs_dir() == 1
    assert not (tmp_path / "prereg-abc").exists() and (tmp_path / "unrelated").exists()


def test_artifact_listing_stops_early(tmp_path):
    from prereg.runner import _read_artifacts
    for i in range(500):
        (tmp_path / f"{i}.png").write_bytes(b"\x89PNG")
    assert len(_read_artifacts(tmp_path)) == config.MAX_ARTIFACTS
