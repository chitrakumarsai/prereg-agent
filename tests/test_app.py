import json

from conftest import SANDBOX
from fastapi.testclient import TestClient

from prereg.app import app
from prereg.runs import RateLimiter

client = TestClient(app)


def _events(run_id: str) -> list[dict]:
    with client.stream("GET", f"/api/runs/{run_id}/events") as resp:
        return [json.loads(line[6:]) for line in resp.iter_lines() if line.startswith("data: {\"id\"")]


def test_health_and_datasets():
    assert client.get("/api/health").json()["ok"] is True
    ids = {d["id"] for d in client.get("/api/datasets").json()}
    assert {"checkout_ab_test", "support_tickets", "pricing_discounts"} <= ids


def test_unknown_dataset_is_404():
    assert client.get("/api/datasets/../../etc/passwd.csv").status_code == 404
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
