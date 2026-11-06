"""HTTP API. Run: uv run uvicorn prereg.app:app --port 8000"""

import asyncio
import json
import logging
import os
import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from prereg import agent, config
from prereg.runs import QueueFull, RateLimiter, Run, RunStore, StreamCounter

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="Prereg", docs_url="/api/docs", openapi_url="/api/openapi.json")
# Local development only (Next on :3000, API on :8000). Production is same-origin behind Caddy.
if cors := os.environ.get("PREREG_CORS_ORIGINS"):
    app.add_middleware(CORSMiddleware, allow_origins=cors.split(","), allow_methods=["GET", "POST"], allow_headers=["*"])
store = RunStore()
limiter = RateLimiter(config.RATE_LIMIT_RUNS, config.RATE_LIMIT_WINDOW_S)
DATASETS: list[dict] = json.loads((config.DEMO_DIR / "datasets.json").read_text())
DATASET_IDS = {d["id"] for d in DATASETS}
SSE_POLL_S = 15
streams = StreamCounter()  # each live stream parks a worker thread; capped below the pool size


class ConsoleRequest(BaseModel):
    code: str = Field(min_length=1, max_length=config.MAX_CONSOLE_CODE_CHARS)
    dataset: str | None = None


def _parse_last_event_id(header: str | None) -> int:
    """Index of the first event to send. Bad or negative values replay from the start."""
    try:
        return max(int(header or "-1") + 1, 0)
    except ValueError:
        return 0


def _client(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")  # set by Caddy in production
    return forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")


def _check_rate(request: Request) -> None:
    if not limiter.allow(_client(request)):
        raise HTTPException(429, "Too many runs from your address. Try again in a few minutes.")


def _start(kind: str, work) -> dict:
    try:
        return {"run_id": store.start(kind, work).id}
    except QueueFull:
        raise HTTPException(503, "The sandbox queue is full. Try again in a minute.") from None


def _demo_path(dataset: str) -> Path:
    if dataset not in DATASET_IDS:
        raise HTTPException(404, "Unknown dataset")
    return config.DEMO_DIR / f"{dataset}.csv"


async def _save_upload(upload: UploadFile) -> Path:
    if not (upload.filename or "").lower().endswith(".csv"):
        raise HTTPException(400, "Please upload a .csv file")
    fd, name = tempfile.mkstemp(suffix=".csv", prefix="upload-")
    tmp = Path(name)
    size = 0
    try:
        with os.fdopen(fd, "wb") as fh:
            while chunk := await upload.read(64_000):
                size += len(chunk)
                if size > config.MAX_UPLOAD_BYTES:
                    raise HTTPException(413, f"CSV is larger than {config.MAX_UPLOAD_BYTES // 1_000_000} MB")
                fh.write(chunk)
        if size == 0:
            raise HTTPException(400, "The file is empty")
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return tmp


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "runtime": config.SANDBOX_RUNTIME, "image": config.SANDBOX_IMAGE, "model": config.MODEL,
            "docker": shutil.which("docker") is not None}


@app.get("/api/policy")
def policy() -> dict:
    return agent.sandbox_policy()


@app.get("/api/datasets")
def datasets() -> list[dict]:
    return DATASETS


@app.get("/api/datasets/{dataset}.csv")
def dataset_file(dataset: str) -> FileResponse:
    return FileResponse(_demo_path(dataset), media_type="text/csv", filename=f"{dataset}.csv")


@app.post("/api/runs")
async def create_run(
    request: Request,
    question: str = Form(min_length=5, max_length=config.MAX_QUESTION_CHARS),
    dataset: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
) -> dict:
    if (dataset is None) == (file is None):
        raise HTTPException(400, "Send either a demo dataset id or a CSV file")
    _check_rate(request)
    upload = await _save_upload(file) if file is not None else None
    csv_path = upload or _demo_path(dataset)

    def work(run: Run) -> None:
        try:
            agent.analyse(csv_path, question.strip(), run.emit)
        finally:
            if upload is not None:
                upload.unlink(missing_ok=True)

    try:
        return _start("analysis", work)
    except HTTPException:
        if upload is not None:
            upload.unlink(missing_ok=True)
        raise


@app.post("/api/console")
def create_console_run(request: Request, body: ConsoleRequest) -> dict:
    _check_rate(request)
    csv_path = _demo_path(body.dataset) if body.dataset else None
    return _start("console", lambda run: agent.run_console(body.code, run.emit, csv_path))


@app.get("/api/runs/{run_id}/events")
async def run_events(run_id: str, request: Request) -> StreamingResponse:
    run = store.get(run_id)
    if run is None:
        raise HTTPException(404, "Run not found or expired")
    start = _parse_last_event_id(request.headers.get("last-event-id"))
    if streams.active >= config.MAX_LIVE_STREAMS:
        raise HTTPException(503, "Too many live viewers right now. Try again shortly.")

    async def stream():
        index = start
        streams.enter()  # counted inside the generator so the matching exit always runs
        try:
            while True:
                events, done = await asyncio.to_thread(run.wait_from, index, SSE_POLL_S)
                for event in events:
                    yield f"id: {event['id']}\nevent: message\ndata: {json.dumps(event)}\n\n"
                index += len(events)
                if done and not events:
                    yield "event: end\ndata: {}\n\n"
                    return
                if not events:
                    yield ": keep-alive\n\n"
                if await request.is_disconnected():
                    return
        finally:
            streams.exit()

    headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    return StreamingResponse(stream(), media_type="text/event-stream", headers=headers)
