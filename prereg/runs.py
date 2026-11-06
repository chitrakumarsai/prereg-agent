"""In-memory run registry: background workers append events, SSE readers replay and follow them."""

import logging
import math
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


class StreamCounter:
    """Counts live SSE streams against a cap; checking and counting happen in one step."""

    def __init__(self, limit: int) -> None:
        self.active = 0
        self._limit = limit
        self._lock = threading.Lock()

    def try_enter(self) -> bool:
        with self._lock:
            if self.active >= self._limit:
                return False
            self.active += 1
            return True

    def exit(self) -> None:
        with self._lock:
            self.active -= 1


class RunStore:
    def __init__(self, max_pending: int = config.MAX_QUEUED_RUNS) -> None:
        self._runs: dict[str, Run] = {}
        self._lock = threading.Lock()
        self._max_pending = max_pending

    def get(self, run_id: str) -> Run | None:
        with self._lock:
            return self._runs.get(run_id)

    def start(self, kind: str, work: Callable[[Run], None]) -> Run:
        run = Run(id=uuid.uuid4().hex[:16], kind=kind)
        with self._lock:
            self._prune()
            if sum(not r.done for r in self._runs.values()) >= self._max_pending:
                raise QueueFull
            self._runs[run.id] = run
        threading.Thread(target=self._execute, args=(run, work), daemon=True, name=f"run-{run.id}").start()
        return run

    def _execute(self, run: Run, work: Callable[[Run], None]) -> None:
        try:
            work(run)
        except Exception as exc:  # noqa: BLE001 - every failure must reach the user as an event
            log.exception("run %s failed", run.id)
            run.emit("error", {"message": str(exc)[:500] or type(exc).__name__})
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
