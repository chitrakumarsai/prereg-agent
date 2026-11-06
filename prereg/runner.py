"""Run untrusted Python inside a throwaway gVisor container.

The sandbox gets: the CSV read-only at /data/input.csv, the script read-only under /code,
an empty writable /out, and nothing else: no network, no secrets, no host environment.
"""

import base64
import json
import logging
import os
import shutil
import stat
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
MAX_LINE_CHARS = 2_000  # longer output lines are split; bounds host memory per read
MAX_LOG_LINES = 2_000
LINE_OVERHEAD = 64  # so a flood of empty lines still counts against the byte budget
_sandbox_slots = threading.BoundedSemaphore(config.MAX_CONCURRENT_SANDBOXES)


def build_command(name: str, data_dir: Path, code_dir: Path, out_dir: Path, entry: str, timeout_s: int) -> list[str]:
    """The full `docker run` argv. Every containment control is here, in one place."""
    return [
        "docker", "run", "--rm", "--name", name, "--hostname", "sandbox",
        "--log-driver", "none",  # output reaches us over the attached stream; dockerd keeps no copy
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
        # env -i first, so PID 1 (and /proc/1/environ) already has the empty environment.
        "env", "-i", *config.SANDBOX_ENV,
        "timeout", "-k", "2", str(timeout_s),
        "python", "-u", "-I", f"/code/{entry}",
    ]


def _prepare(run_dir: Path, csv_path: Path | None, files: dict[str, bytes]) -> tuple[Path, Path, Path]:
    data_dir, code_dir, out_dir = run_dir / "data", run_dir / "code", run_dir / "out"
    for d in (data_dir, code_dir, out_dir):
        d.mkdir(parents=True)
        d.chmod(0o755)
    if config.SCRATCH_TMPFS:
        # Production: a private, size-capped mount per run, so one run cannot starve another.
        subprocess.run(
            ["mount", "-t", "tmpfs", "-o", f"size={config.SCRATCH_SIZE},nr_inodes=4096,mode=0777,nosuid,nodev,noexec", "tmpfs",
             str(out_dir)],
            check=True, capture_output=True, timeout=10,
        )
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
    """Drain the container's output with bounded host memory: each read is capped, and so is what is kept."""
    while chunk := stream.readline(MAX_LINE_CHARS):
        if state["truncated"]:
            continue  # keep draining so the container never blocks on a full pipe
        line = chunk.rstrip("\n")
        state["bytes"] += len(line) + LINE_OVERHEAD
        if state["bytes"] > config.MAX_LOG_BYTES or len(sink) >= MAX_LOG_LINES:
            state["truncated"] = True
            continue
        sink.append(line)
        if on_line is not None:
            on_line(line)


def _read_regular_file(path: Path, limit: int) -> bytes | None:
    """Read a file the sandbox wrote, refusing symlinks and anything that is not a plain file."""
    try:
        # O_NONBLOCK: a FIFO planted by the sandbox must not hang the host on open().
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        return None
    with os.fdopen(fd, "rb") as fh:
        info = os.fstat(fh.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            return None
        return fh.read(limit + 1)


def _read_result(out_dir: Path) -> tuple[dict | None, str | None]:
    path = out_dir / "result.json"
    if not path.exists() and not path.is_symlink():
        return None, "the script did not write /out/result.json"
    raw = _read_regular_file(path, config.MAX_RESULT_BYTES)
    if raw is None:
        return None, "result.json must be a regular file under 256 KB (symlinks are refused)"
    try:
        data = json.loads(raw.decode())
    except (ValueError, RecursionError) as exc:  # ValueError covers JSONDecodeError, Unicode and huge-int errors
        return None, f"result.json is not valid JSON: {str(exc)[:200]}"
    if not isinstance(data, dict):
        return None, "result.json must contain a JSON object"
    return data, None


def _read_artifacts(out_dir: Path) -> dict[str, str]:
    artifacts: dict[str, str] = {}
    with os.scandir(out_dir) as entries:  # stops early: a run may leave thousands of files
        for entry in entries:
            if len(artifacts) >= config.MAX_ARTIFACTS:
                break
            if entry.name.endswith(".png"):
                raw = _read_regular_file(Path(entry.path), config.MAX_ARTIFACT_BYTES)
                if raw is not None:
                    artifacts[entry.name] = base64.b64encode(raw).decode()
    return artifacts


def _destroy(run_dir: Path) -> None:
    out_dir = run_dir / "out"
    if config.SCRATCH_TMPFS and os.path.ismount(out_dir):
        try:
            done = subprocess.run(["umount", "-l", str(out_dir)], capture_output=True, text=True, timeout=10)
            if done.returncode != 0:
                log.error("could not unmount %s: %s", out_dir, done.stderr.strip())
        except subprocess.TimeoutExpired:
            log.error("unmounting %s timed out", out_dir)
    shutil.rmtree(run_dir, ignore_errors=True)


def sweep_runs_dir() -> int:
    """Remove run folders left behind by a crash or restart. Called once at startup."""
    if not config.RUNS_DIR.is_dir():
        return 0
    leftovers = [p for p in config.RUNS_DIR.glob("prereg-*") if p.is_dir()]
    for path in leftovers:
        _destroy(path)
    uploads = list(config.RUNS_DIR.glob("upload-*.csv"))
    for path in uploads:
        path.unlink(missing_ok=True)
    return len(leftovers) + len(uploads)


def _classify(exit_code: int, duration_s: float, timeout_s: int) -> str:
    if exit_code == 0:
        return "ok"
    if exit_code == EXIT_TIMEOUT:
        return "timeout"
    if exit_code == EXIT_SIGKILL:  # `timeout -k` escalation, or the memory/pids limit
        return "timeout" if duration_s >= timeout_s else "killed"
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
    # Only containers take a slot; model calls between them do not.
    with _sandbox_slots:
        return _run(csv_path, files, entry, timeout_s, on_line)


def _run(
    csv_path: Path | None, files: dict[str, bytes], entry: str, timeout_s: int, on_line: LineCallback | None
) -> RunResult:
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
        hung = False
        try:
            exit_code = proc.wait(timeout=timeout_s + GRACE_S)
        except subprocess.TimeoutExpired:
            log.warning("sandbox %s ignored its timeout; force-removing", name)
            hung = True
            try:
                subprocess.run(["docker", "rm", "-f", name], capture_output=True, check=False, timeout=30)
            except subprocess.TimeoutExpired:
                log.error("docker rm -f %s timed out; dockerd may be stuck", name)
            finally:
                proc.kill()
                exit_code = proc.wait()
        pump.join(timeout=5)
        duration = time.monotonic() - started
        result, result_error = _read_result(out_dir)
        return RunResult(
            status="timeout" if hung else _classify(exit_code, duration, timeout_s),
            exit_code=exit_code,
            duration_s=round(duration, 2),
            log="\n".join(lines),
            log_truncated=state["truncated"],
            result=result,
            result_error=result_error,
            artifacts=_read_artifacts(out_dir),
        )
    finally:
        _destroy(run_dir)
