"""Data shapes shared by the agent, the runner, the verifier and the API."""

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

TestName = Literal["welch_t", "mann_whitney", "chi_square", "ols"]

TEST_LABELS: dict[str, str] = {
    "welch_t": "Welch's t-test",
    "mann_whitney": "Mann-Whitney U test",
    "chi_square": "Chi-square test of independence",
    "ols": "Ordinary least squares regression",
}


class AnalysisPlan(BaseModel):
    """The pre-registered plan. Frozen: once created it cannot be edited, only fingerprinted."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    hypothesis: str = Field(min_length=5, max_length=600)
    test: TestName
    outcome: str = Field(min_length=1, max_length=200)
    predictor: str = Field(min_length=1, max_length=200)
    alpha: float = Field(gt=0, lt=0.5)
    decision_rule: str = Field(min_length=5, max_length=400)
    rationale: str = Field(default="", max_length=800)

    def fingerprint(self) -> str:
        canonical = json.dumps(self.model_dump(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()


class RunResult(BaseModel):
    """What came back from one sandboxed execution."""

    model_config = ConfigDict(frozen=True)

    status: Literal["ok", "error", "timeout", "killed"]
    exit_code: int
    duration_s: float
    log: str
    log_truncated: bool = False
    result: dict[str, Any] | None = None
    result_error: str | None = None
    artifacts: dict[str, str] = Field(default_factory=dict)  # filename -> base64 png


class Check(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    passed: bool
    detail: str


class Verification(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    checks: tuple[Check, ...]
    recomputed: dict[str, Any] | None = None
