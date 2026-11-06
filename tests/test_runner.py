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
def test_run_folder_is_destroyed(demo_csv):
    run_in_sandbox(demo_csv, {"a.py": b"print('hi')"}, "a.py")
    assert not any(config.RUNS_DIR.glob("prereg-*"))
