"""The agent loop: profile -> pre-register -> freeze -> code -> run -> verify -> explain.

Every step reports progress through `emit(event_type, data)` so the UI can show it live.
Run from the command line: uv run python -m prereg.agent demo/checkout_ab_test.csv "question"
"""

import json
import logging
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from prereg import config, llm, prompts
from prereg.runner import build_command, run_in_sandbox
from prereg.schema import TEST_LABELS, AnalysisPlan, RunResult
from prereg.verifier import compare, profile_in_sandbox, recompute_in_sandbox, validate_plan

log = logging.getLogger(__name__)

Emit = Callable[[str, dict], None]
LOG_TAIL_CHARS = 2500


class AgentError(RuntimeError):
    """A step failed in a way the agent could not recover from."""


def _sandbox_logger(emit: Emit, stage: str) -> Callable[[str], None]:
    return lambda line: emit("log", {"stage": stage, "line": line})


def _run_summary(run: RunResult) -> dict:
    return {"status": run.status, "exit_code": run.exit_code, "duration_s": run.duration_s}


def sandbox_policy() -> dict:
    """The containment controls, as shown to users and written into every receipt."""
    return {
        "runtime": f"{config.SANDBOX_RUNTIME} (gVisor)" if config.SANDBOX_RUNTIME == "runsc" else config.SANDBOX_RUNTIME,
        "image": config.SANDBOX_IMAGE,
        "network": "none",
        "memory": config.MEMORY_LIMIT,
        "cpus": config.CPU_LIMIT,
        "pids": config.PIDS_LIMIT,
        "timeout_s": config.RUN_TIMEOUT_S,
        "filesystem": "read-only root, /data read-only, /out write-only scratch",
        "environment": "empty (PATH, HOME, MPLCONFIGDIR only)",
        "user": "uid 1000, all capabilities dropped, no-new-privileges",
        "lifecycle": "container and run folder destroyed after every step",
        "command": " ".join(build_command("<id>", Path("<run>/data"), Path("<run>/code"), Path("<run>/out"), "<script>.py", config.RUN_TIMEOUT_S)),
    }


def profile_data(csv_path: Path, emit: Emit) -> dict:
    emit("stage", {"stage": "profile", "status": "running"})
    run = profile_in_sandbox(csv_path, _sandbox_logger(emit, "profile"))
    if run.status != "ok" or run.result is None:
        raise AgentError(f"could not read the CSV: {run.result_error or run.log[-500:]}")
    profile = run.result
    emit("profile", {"rows": profile["rows"], "columns": profile["columns"], "suspicious": profile["suspicious"],
                     "versions": profile["versions"], "run": _run_summary(run)})
    if profile["suspicious"]:
        emit("alert", {"kind": "injection", "message": f"{len(profile['suspicious'])} cell(s) contain instruction-like "
                       "text. Treated strictly as data.", "cells": profile["suspicious"]})
    emit("stage", {"stage": "profile", "status": "done"})
    return profile


def preregister(question: str, profile: dict, emit: Emit) -> tuple[AnalysisPlan, str]:
    emit("stage", {"stage": "plan", "status": "running"})
    feedback: str | None = None
    for attempt in range(1, config.MAX_PLAN_ATTEMPTS + 1):
        text, model = llm.chat(prompts.plan_messages(question, profile, feedback), max_tokens=1500)
        try:
            plan = AnalysisPlan(**llm.extract_json(text))
            problems = validate_plan(plan, profile)
        except (llm.LLMError, ValidationError, TypeError) as exc:
            plan, problems = None, [str(exc)[:400]]
        if plan is not None and not problems:
            frozen_at = datetime.now(UTC).isoformat(timespec="seconds")
            emit("plan", {"plan": plan.model_dump(), "test_label": TEST_LABELS[plan.test], "model": model,
                          "fingerprint": plan.fingerprint(), "frozen_at": frozen_at, "attempt": attempt})
            emit("stage", {"stage": "plan", "status": "done"})
            return plan, frozen_at
        feedback = "; ".join(problems)
        emit("retry", {"stage": "plan", "attempt": attempt, "reason": feedback})
    raise AgentError(f"could not produce a valid plan: {feedback}")


def execute(plan: AnalysisPlan, profile: dict, csv_path: Path, emit: Emit) -> tuple[str, RunResult, int]:
    emit("stage", {"stage": "execute", "status": "running"})
    previous: tuple[str, str] | None = None
    for attempt in range(1, config.MAX_CODE_ATTEMPTS + 1):
        text, model = llm.chat(prompts.code_messages(plan, profile, previous), max_tokens=3500)
        code = llm.extract_code(text)
        emit("code", {"code": code, "attempt": attempt, "model": model})
        run = run_in_sandbox(csv_path, {"analysis.py": code.encode()}, "analysis.py",
                             on_line=_sandbox_logger(emit, "execute"))
        emit("run", {"attempt": attempt, **_run_summary(run), "result_error": run.result_error})
        if run.status == "ok" and run.result is not None:
            emit("stage", {"stage": "execute", "status": "done"})
            return code, run, attempt
        reason = run.result_error if run.status == "ok" else f"status {run.status}, exit code {run.exit_code}"
        previous = (code, f"{reason}\n--- sandbox log tail ---\n{run.log[-LOG_TAIL_CHARS:]}")
        emit("retry", {"stage": "execute", "attempt": attempt, "reason": reason})
    raise AgentError(f"the analysis did not succeed after {config.MAX_CODE_ATTEMPTS} attempts")


def verify(plan: AnalysisPlan, claimed: dict, csv_path: Path, emit: Emit):
    emit("stage", {"stage": "verify", "status": "running"})
    run = recompute_in_sandbox(plan, csv_path, _sandbox_logger(emit, "verify"))
    if run.status != "ok" or run.result is None:
        raise AgentError(f"independent recomputation failed: {run.result_error or run.log[-500:]}")
    verification = compare(plan, claimed, run.result)
    emit("verify", verification.model_dump())
    emit("stage", {"stage": "verify", "status": "done"})
    return verification


def explain(question: str, plan: AnalysisPlan, verification, emit: Emit) -> str:
    emit("stage", {"stage": "explain", "status": "running"})
    text, _ = llm.chat(prompts.explain_messages(question, plan, verification.recomputed, verification.passed),
                       max_tokens=600)
    emit("explain", {"text": text})
    emit("stage", {"stage": "explain", "status": "done"})
    return text


def analyse(csv_path: Path, question: str, emit: Emit) -> dict:
    """Run the whole pipeline and return the receipt."""
    started = time.monotonic()
    profile = profile_data(csv_path, emit)
    plan, frozen_at = preregister(question, profile, emit)
    code, run, attempts = execute(plan, profile, csv_path, emit)
    verification = verify(plan, run.result, csv_path, emit)
    explanation = explain(question, plan, verification, emit)
    receipt = {
        "question": question,
        "plan": plan.model_dump(),
        "test_label": TEST_LABELS[plan.test],
        "fingerprint": plan.fingerprint(),
        "frozen_at": frozen_at,
        "code": code,
        "code_attempts": attempts,
        "result": run.result,
        "chart": run.artifacts.get("chart.png"),
        "verification": verification.model_dump(),
        "explanation": explanation,
        "versions": profile["versions"],
        "models": {"primary": config.MODEL, "fallback": config.FALLBACK_MODEL},
        "sandbox": sandbox_policy(),
        "suspicious_cells": len(profile["suspicious"]),
        "duration_s": round(time.monotonic() - started, 1),
        "completed_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    emit("receipt", receipt)
    return receipt


def run_console(code: str, emit: Emit, csv_path: Path | None = None) -> RunResult:
    """Run user-supplied code in the same sandbox, for the 'try to break it' console."""
    emit("stage", {"stage": "console", "status": "running"})
    run = run_in_sandbox(csv_path, {"attempt.py": code.encode()}, "attempt.py",
                         on_line=_sandbox_logger(emit, "console"))
    emit("run", _run_summary(run))
    emit("stage", {"stage": "console", "status": "done"})
    return run


def _cli() -> None:
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) != 3:
        raise SystemExit("usage: python -m prereg.agent <csv> <question>")

    def emit(kind: str, data: dict) -> None:
        if kind == "log":
            print(f"  [{data['stage']}] {data['line']}")
        elif kind == "receipt":
            print(json.dumps({k: v for k, v in data.items() if k not in ("chart", "code")}, indent=2))
        elif kind != "code":
            print(f"{kind}: {json.dumps(data)[:300]}")

    analyse(Path(sys.argv[1]), sys.argv[2], emit)


if __name__ == "__main__":
    _cli()
