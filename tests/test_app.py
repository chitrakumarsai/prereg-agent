import json

from conftest import SANDBOX
from fastapi.testclient import TestClient

import pytest
from fastapi import HTTPException

from prereg.app import _demo_path, _parse_last_event_id, app
from prereg.runs import QueueFull, RateLimiter, RunStore

client = TestClient(app)


def _events(run_id: str) -> list[dict]:
    with client.stream("GET", f"/api/runs/{run_id}/events") as resp:
        return [json.loads(line[6:]) for line in resp.iter_lines() if line.startswith("data: {\"id\"")]


def test_health_and_datasets():
    assert client.get("/api/health").json()["ok"] is True
    ids = {d["id"] for d in client.get("/api/datasets").json()}
    assert {"checkout_ab_test", "support_tickets", "pricing_discounts"} <= ids


def test_unknown_dataset_is_404():
    with pytest.raises(HTTPException) as exc:
        _demo_path("../../etc/passwd")
    assert exc.value.status_code == 404
    assert client.get("/api/datasets/%2e%2e%2fsecret.csv").status_code == 404
    resp = client.post("/api/runs", data={"question": "Does it differ?", "dataset": "nope"})
    assert resp.status_code == 404


def test_run_needs_exactly_one_source():
    assert client.post("/api/runs", data={"question": "Does it differ?"}).status_code == 400


def test_upload_must_be_csv():
    files = {"file": ("evil.py", b"print(1)", "text/plain")}
    resp = client.post("/api/runs", data={"question": "Does it differ?"}, files=files)
    assert resp.status_code == 400


def test_unknown_run_is_404():
    assert client.get("/api/runs/doesnotexist/events").status_code == 404


def test_rate_limiter_blocks_after_limit():
    limiter = RateLimiter(limit=2, window_s=60)
    assert limiter.allow("a") and limiter.allow("a")
    assert not limiter.allow("a")
    assert limiter.allow("b")


@SANDBOX
def test_console_streams_sandbox_output():
    run_id = client.post("/api/console", json={"code": "print('hello from inside')"}).json()["run_id"]
    events = _events(run_id)
    lines = [e["data"]["line"] for e in events if e["type"] == "log"]
    assert "hello from inside" in lines
    assert any(e["type"] == "run" and e["data"]["status"] == "ok" for e in events)


@pytest.mark.parametrize(("header", "expected"), [(None, 0), ("4", 5), ("-5", 0), ("abc", 0)])
def test_last_event_id_is_parsed_defensively(header, expected):
    assert _parse_last_event_id(header) == expected


def test_queue_cap_rejects_new_runs():
    import threading
    gate = threading.Event()
    store = RunStore(max_pending=1)
    store.start("x", lambda run: gate.wait(5))
    with pytest.raises(QueueFull):
        store.start("x", lambda run: None)
    gate.set()


def test_nan_in_events_reaches_the_browser_as_valid_json():
    from prereg.app import store
    def work(run):
        run.emit("verify", {"recomputed": {"statistic": float("nan"), "p_value": float("inf")}, "checks": []})
    run_id = store.start("analysis", work).id
    events = _events(run_id)
    verify = next(e for e in events if e["type"] == "verify")
    assert verify["data"]["recomputed"] == {"statistic": None, "p_value": None}


def test_stream_counter_is_atomic_and_capped():
    from prereg.runs import StreamCounter
    counter = StreamCounter(limit=2, per_client=5)
    assert counter.try_enter() and counter.try_enter()
    assert not counter.try_enter()
    counter.exit()
    assert counter.try_enter()


def test_one_client_cannot_fill_the_queue():
    import threading
    from prereg.runs import ClientBusy
    gate = threading.Event()
    store = RunStore(max_pending=8, per_client=1)
    store.start("x", lambda run: gate.wait(5), client="a")
    with pytest.raises(ClientBusy):
        store.start("x", lambda run: None, client="a")
    store.start("x", lambda run: None, client="b")  # someone else still gets in
    gate.set()


def test_stream_cap_is_per_client_too():
    from prereg.runs import StreamCounter
    counter = StreamCounter(limit=10, per_client=1)
    assert counter.try_enter("a") and not counter.try_enter("a")
    assert counter.try_enter("b")
    counter.exit("a")
    assert counter.try_enter("a")


def test_busy_client_gets_429_and_no_upload_is_left(monkeypatch, tmp_path):
    import threading
    from prereg import app as app_module
    from prereg import config
    monkeypatch.setattr(config, "RUNS_DIR", tmp_path)
    gate = threading.Event()
    busy_store = RunStore(max_pending=8, per_client=1)
    monkeypatch.setattr(app_module, "store", busy_store)
    busy_store.start("x", lambda run: gate.wait(5), client="testclient")
    files = {"file": ("data.csv", b"g,v\na,1\nb,2\n", "text/csv")}
    resp = client.post("/api/runs", data={"question": "Does it differ?"}, files=files)
    gate.set()
    assert resp.status_code == 429
    assert not list(tmp_path.glob("upload-*.csv"))


def test_host_errors_are_not_shown_to_users():
    store = RunStore()
    def work(run):
        raise OSError("mount /var/lib/prereg/runs/prereg-1/out failed")
    run = store.start("x", work)
    import time
    for _ in range(50):
        if run.done:
            break
        time.sleep(0.05)
    message = next(e["data"]["message"] for e in run.events if e["type"] == "error")
    assert "/var/lib" not in message
