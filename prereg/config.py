"""Runtime settings. Everything tunable lives here; secrets come only from the environment."""

import os
from pathlib import Path

SANDBOX_IMAGE = os.environ.get("PREREG_SANDBOX_IMAGE", "prereg-sandbox:1")
SANDBOX_RUNTIME = os.environ.get("PREREG_SANDBOX_RUNTIME", "runsc")
RUNS_DIR = Path(os.environ.get("PREREG_RUNS_DIR", "/tmp/prereg-runs"))

RUN_TIMEOUT_S = int(os.environ.get("PREREG_RUN_TIMEOUT_S", "30"))
MEMORY_LIMIT = "512m"
CPU_LIMIT = "1"
PIDS_LIMIT = 128
TMPFS_SIZE = "64m"
SANDBOX_UID = "1000:1000"
# The only variables the sandboxed process ever sees.
SANDBOX_ENV = ("PATH=/usr/local/bin:/usr/bin:/bin", "HOME=/tmp", "MPLCONFIGDIR=/tmp/mpl")

MAX_LOG_BYTES = 64_000
MAX_RESULT_BYTES = 1_000_000
MAX_ARTIFACT_BYTES = 2_000_000
MAX_ARTIFACTS = 3

INFERENCE_BASE_URL = "https://api.vultrinference.com/v1"
MODEL = os.environ.get("PREREG_MODEL", "deepseek-v4.1-flash-1017")
FALLBACK_MODEL = os.environ.get("PREREG_FALLBACK_MODEL", "mimo-v2.6-pro")
LLM_TIMEOUT_S = 90
MAX_PLAN_ATTEMPTS = 2
MAX_CODE_ATTEMPTS = 3

MAX_UPLOAD_BYTES = 5_000_000
MAX_QUESTION_CHARS = 500
MAX_CONSOLE_CODE_CHARS = 20_000
MAX_CONCURRENT_SANDBOXES = int(os.environ.get("PREREG_MAX_CONCURRENT", "2"))
RATE_LIMIT_RUNS = 12
RATE_LIMIT_WINDOW_S = 600
RUN_RETENTION_S = 3600
MAX_QUEUED_RUNS = 8  # unfinished runs (thinking, queued or in a sandbox), across all clients
MAX_LIVE_STREAMS = 24  # concurrent SSE viewers; streams poll memory and hold no threads
MAX_RETAINED_RUNS = 100  # finished runs kept for replay, oldest dropped first

DEMO_DIR = Path(__file__).resolve().parent.parent / "demo"
