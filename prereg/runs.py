"""In-memory run registry: background workers append events, SSE readers replay and follow them."""

import logging
import math
import subprocess
import threading
import time
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from prereg import config

log = logging.getLogger(__name__)


def json_safe(value: Any) -> Any:
    """Copy of `value` with NaN and infinities replaced by None: browsers' JSON.parse rejects them."""
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [json_safe(v) for v in value]
    return value


@dataclass
class Run:
    id: str
    kind: str
    client: str = ""
    created: float = field(default_factory=time.time)
    events: list[dict] = field(default_factory=list)
    done: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)

    def emit(self, kind: str, data: dict) -> None:
        event = {"id": 0, "type": kind, "t": round(time.time() - self.created, 2), "data": json_safe(data)}
        with self.lock:
            self.events.append({**event, "id": len(self.events)})

    def finish(self) -> None:
        with self.lock:
            self.done = True

    def read_from(self, index: int) -> tuple[list[dict], bool]:
        """Events from `index` on, and whether the run has finished. Never blocks."""
        with self.lock:
            return self.events[index:], self.done


class QueueFull(RuntimeError):
    """Too many runs are already waiting for or holding a sandbox slot."""


class ClientBusy(RuntimeError):
    """This client already has its maximum number of unfinished runs."""


class StreamCounter:
    """Counts live SSE streams against a global and a per-client cap; check and count are one step."""

    def __init__(self, limit: int, per_client: int) -> None:
        self.active = 0
        self._limit, self._per_client = limit, per_client
        self._by_client: dict[str, int] = {}
        self._lock = threading.Lock()

    def try_enter(self, client: str = "") -> bool:
        with self._lock:
            mine = self._by_client.get(client, 0)
            if self.active >= self._limit or mine >= self._per_client:
                return False
            self.active += 1
            self._by_client[client] = mine + 1
            return True

    def exit(self, client: str = "") -> None:
        with self._lock:
            self.active -= 1
            remaining = self._by_client.get(client, 1) - 1
            if remaining > 0:
                self._by_client[client] = remaining
            else:
                self._by_client.pop(client, None)


class RunStore:
    def __init__(
        self, max_pending: int = config.MAX_QUEUED_RUNS, per_client: int = config.MAX_RUNS_PER_CLIENT
    ) -> None:
        self._runs: dict[str, Run] = {}
        self._lock = threading.Lock()
        self._max_pending, self._per_client = max_pending, per_client

    def is_busy(self, client: str) -> bool:
        with self._lock:
            return sum(not r.done and r.client == client for r in self._runs.values()) >= self._per_client

    def get(self, run_id: str) -> Run | None:
        with self._lock:
            return self._runs.get(run_id)

    def start(self, kind: str, work: Callable[[Run], None], client: str = "") -> Run:
        run = Run(id=uuid.uuid4().hex[:16], kind=kind, client=client)
        with self._lock:
            self._prune()
            unfinished = [r for r in self._runs.values() if not r.done]
            if sum(r.client == client for r in unfinished) >= self._per_client:
                raise ClientBusy
            if len(unfinished) >= self._max_pending:
                raise QueueFull
            self._runs[run.id] = run
        threading.Thread(target=self._execute, args=(run, work), daemon=True, name=f"run-{run.id}").start()
        return run

    def _execute(self, run: Run, work: Callable[[Run], None]) -> None:
        try:
            work(run)
        except Exception as exc:  # noqa: BLE001 - every failure must reach the user as an event
            log.exception("run %s failed", run.id)
            # Host-side failures (mounts, copies) would expose server paths; keep their detail in the log.
            hidden = isinstance(exc, OSError | subprocess.SubprocessError)
            message = "The server could not prepare the sandbox. Please try again." if hidden else str(exc)[:500]
            run.emit("error", {"message": message or type(exc).__name__})
        finally:
            run.finish()

    def _prune(self) -> None:
        cutoff = time.time() - config.RUN_RETENTION_S
        finished = sorted((r for r in self._runs.values() if r.done), key=lambda r: r.created)
        excess = max(len(finished) - config.MAX_RETAINED_RUNS, 0)
        for i, run in enumerate(finished):
            if i < excess or run.created < cutoff:
                del self._runs[run.id]


class RateLimiter:
    """Sliding-window limit per client address."""

    def __init__(self, limit: int, window_s: float) -> None:
        self._limit, self._window = limit, window_s
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, client: str) -> bool:
        now = time.time()
        with self._lock:
            # forget clients whose whole window has expired, so the table cannot grow without bound
            stale = [c for c, h in self._hits.items() if not h or h[-1] < now - self._window]
            for c in stale:
                del self._hits[c]
            hits = self._hits.setdefault(client, deque())
            while hits and hits[0] < now - self._window:
                hits.popleft()
            if len(hits) >= self._limit:
                return False
            hits.append(now)
            return True
