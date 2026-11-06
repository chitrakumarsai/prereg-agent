import shutil
import subprocess
from pathlib import Path

import pytest

from prereg import config

ROOT = Path(__file__).resolve().parent.parent


def _sandbox_available() -> bool:
    if shutil.which("docker") is None:
        return False
    probe = subprocess.run(
        ["docker", "image", "inspect", config.SANDBOX_IMAGE], capture_output=True, check=False
    )
    runtimes = subprocess.run(
        ["docker", "info", "--format", "{{json .Runtimes}}"], capture_output=True, text=True, check=False
    )
    return probe.returncode == 0 and config.SANDBOX_RUNTIME in runtimes.stdout


SANDBOX = pytest.mark.skipif(not _sandbox_available(), reason="docker with runsc and the sandbox image is required")


@pytest.fixture
def demo_csv() -> Path:
    return ROOT / "demo" / "checkout_ab_test.csv"


@pytest.fixture
def profile() -> dict:
    return {
        "rows": 4,
        "columns": [
            {"name": "variant", "kind": "categorical", "unique": 2},
            {"name": "value", "kind": "numeric", "unique": 4},
            {"name": "units", "kind": "numeric", "unique": 4},
            {"name": "store", "kind": "categorical", "unique": 30},
        ],
    }
