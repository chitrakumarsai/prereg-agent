"""In-memory run registry: background workers append events, SSE readers replay and follow them."""

import logging
import threading
import time
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field

from prereg import config

log = logging.getLogger(__name__)

_sandbox_slots = threading.BoundedSemaphore(config.MAX_CONCURRENT_SANDBOXES)


@dataclass
class Run:
    id: str
    kind: str
    created: float = field(default_factory=time.time)
    events: list[dict] = field(default_factory=list)
    done: bool = False
    cond: threading.Condition = field(default_factory=threading.Condition)

    def emit(self, kind: str, data: dict) -> None:
        with self.cond:
            self.events.append({"id": len(self.events), "type": kind, "t": round(time.time() - self.created, 2),
                                "data": data})
            self.cond.notify_all()

    def finish(self) -> None:
        with self.cond:
            self.done = True
            self.cond.notify_all()

    def wait_from(self, index: int, timeout: float) -> tuple[list[dict], bool]:
        with self.cond:
            if index >= len(self.events) and not self.done:
                self.cond.wait(timeout)
            return self.events[index:], self.done


class RunStore:
    def __init__(self) -> None:
        self._runs: dict[str, Run] = {}
        self._lock = threading.Lock()

    def get(self, run_id: str) -> Run | None:
        with self._lock:
            return self._runs.get(run_id)

    def start(self, kind: str, work: Callable[[Run], None]) -> Run:
        run = Run(id=uuid.uuid4().hex[:16], kind=kind)
        with self._lock:
            self._prune()
            self._runs[run.id] = run
        threading.Thread(target=self._execute, args=(run, work), daemon=True, name=f"run-{run.id}").start()
        return run

    def _execute(self, run: Run, work: Callable[[Run], None]) -> None:
        run.emit("queued", {"message": "waiting for a free sandbox slot"})
        try:
            with _sandbox_slots:
                work(run)
        except Exception as exc:  # noqa: BLE001 - every failure must reach the user as an event
            log.exception("run %s failed", run.id)
            run.emit("error", {"message": str(exc)[:500] or type(exc).__name__})
        finally:
            run.finish()

    def _prune(self) -> None:
        cutoff = time.time() - config.RUN_RETENTION_S
        for run_id in [r.id for r in self._runs.values() if r.done and r.created < cutoff]:
            del self._runs[run_id]


class RateLimiter:
    """Sliding-window limit per client address."""

    def __init__(self, limit: int, window_s: float) -> None:
        self._limit, self._window = limit, window_s
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, client: str) -> bool:
        now = time.time()
        with self._lock:
            hits = self._hits.setdefault(client, deque())
            while hits and hits[0] < now - self._window:
                hits.popleft()
            if len(hits) >= self._limit:
                return False
            hits.append(now)
            return True
