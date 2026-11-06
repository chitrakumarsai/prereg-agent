"""Run untrusted Python inside a throwaway gVisor container.

The sandbox gets: the CSV read-only at /data/input.csv, the script read-only under /code,
an empty writable /out, and nothing else: no network, no secrets, no host environment.
"""

import base64
import json
import logging
import shutil
import subprocess
import threading
import time
import uuid
from collections.abc import Callable
from pathlib import Path

from prereg import config
from prereg.schema import RunResult

log = logging.getLogger(__name__)

LineCallback = Callable[[str], None]
EXIT_TIMEOUT = 124  # coreutils `timeout` after SIGTERM
EXIT_SIGKILL = 137  # SIGKILL: the memory limit, or `timeout -k` escalating
GRACE_S = 20  # extra wait before the host gives up on the docker client itself


def build_command(name: str, data_dir: Path, code_dir: Path, out_dir: Path, entry: str, timeout_s: int) -> list[str]:
    """The full `docker run` argv. Every containment control is here, in one place."""
    return [
        "docker", "run", "--rm", "--name", name, "--hostname", "sandbox",
        "--runtime", config.SANDBOX_RUNTIME,
        "--network", "none",
        "--memory", config.MEMORY_LIMIT, "--memory-swap", config.MEMORY_LIMIT,
        "--cpus", config.CPU_LIMIT,
        "--pids-limit", str(config.PIDS_LIMIT),
        "--read-only", "--tmpfs", f"/tmp:rw,size={config.TMPFS_SIZE}",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--user", config.SANDBOX_UID,
        "-v", f"{data_dir}:/data:ro",
        "-v", f"{code_dir}:/code:ro",
        "-v", f"{out_dir}:/out:rw",
        config.SANDBOX_IMAGE,
        "timeout", "-k", "2", str(timeout_s),
        "env", "-i", *config.SANDBOX_ENV,
        "python", "-u", "-I", f"/code/{entry}",
    ]


def _prepare(run_dir: Path, csv_path: Path | None, files: dict[str, bytes]) -> tuple[Path, Path, Path]:
    data_dir, code_dir, out_dir = run_dir / "data", run_dir / "code", run_dir / "out"
    for d in (data_dir, code_dir, out_dir):
        d.mkdir(parents=True)
        d.chmod(0o755)
    out_dir.chmod(0o777)  # the sandbox user (uid 1000) must be able to write here
    if csv_path is not None:
        target = data_dir / "input.csv"
        shutil.copyfile(csv_path, target)
        target.chmod(0o644)
    for fname, content in files.items():
        if "/" in fname or fname.startswith("."):
            raise ValueError(f"invalid sandbox file name: {fname!r}")
        (code_dir / fname).write_bytes(content)
        (code_dir / fname).chmod(0o644)
    return data_dir, code_dir, out_dir


def _pump(stream, sink: list[str], state: dict, on_line: LineCallback | None) -> None:
    for line in stream:
        line = line.rstrip("\n")
        if state["bytes"] < config.MAX_LOG_BYTES:
            sink.append(line)
            state["bytes"] += len(line) + 1
        else:
            state["truncated"] = True
        if on_line is not None and not state["truncated"]:
            on_line(line)


def _read_result(out_dir: Path) -> tuple[dict | None, str | None]:
    path = out_dir / "result.json"
    if not path.is_file():
        return None, "the script did not write /out/result.json"
    if path.stat().st_size > config.MAX_RESULT_BYTES:
        return None, "result.json is larger than the 1 MB limit"
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return None, f"result.json is not valid JSON: {exc}"
    if not isinstance(data, dict):
        return None, "result.json must contain a JSON object"
    return data, None


def _read_artifacts(out_dir: Path) -> dict[str, str]:
    pngs = sorted(p for p in out_dir.glob("*.png") if p.is_file() and not p.is_symlink())
    return {
        p.name: base64.b64encode(p.read_bytes()).decode()
        for p in pngs[: config.MAX_ARTIFACTS]
        if p.stat().st_size <= config.MAX_ARTIFACT_BYTES
    }


def _classify(exit_code: int, duration_s: float, timeout_s: int) -> str:
    if exit_code == 0:
        return "ok"
    if exit_code == EXIT_TIMEOUT or duration_s >= timeout_s:
        return "timeout"
    if exit_code == EXIT_SIGKILL:
        return "killed"
    return "error"


def run_in_sandbox(
    csv_path: Path | None,
    files: dict[str, bytes],
    entry: str,
    *,
    timeout_s: int = config.RUN_TIMEOUT_S,
    on_line: LineCallback | None = None,
) -> RunResult:
    """Execute `/code/<entry>` in a fresh sandbox, stream its output, then destroy everything."""
    if entry not in files:
        raise ValueError(f"entry {entry!r} is not among the provided files")
    name = f"prereg-{uuid.uuid4().hex[:12]}"
    run_dir = config.RUNS_DIR / name
    started = time.monotonic()
    try:
        data_dir, code_dir, out_dir = _prepare(run_dir, csv_path, files)
        cmd = build_command(name, data_dir, code_dir, out_dir, entry, timeout_s)
        lines: list[str] = []
        state = {"bytes": 0, "truncated": False}
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace", bufsize=1
        )
        pump = threading.Thread(target=_pump, args=(proc.stdout, lines, state, on_line), daemon=True)
        pump.start()
        try:
            exit_code = proc.wait(timeout=timeout_s + GRACE_S)
        except subprocess.TimeoutExpired:
            log.warning("sandbox %s ignored its timeout; force-removing", name)
            subprocess.run(["docker", "rm", "-f", name], capture_output=True, check=False)
            proc.kill()
            exit_code = proc.wait()
        pump.join(timeout=5)
        duration = time.monotonic() - started
        result, result_error = _read_result(out_dir)
        return RunResult(
            status=_classify(exit_code, duration, timeout_s),
            exit_code=exit_code,
            duration_s=round(duration, 2),
            log="\n".join(lines),
            log_truncated=state["truncated"],
            result=result,
            result_error=result_error,
            artifacts=_read_artifacts(out_dir),
        )
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)
