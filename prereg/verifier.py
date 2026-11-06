"""Checks a plan against the data, and the agent's result against an independent recomputation."""

import json
import math
from collections.abc import Callable
from pathlib import Path
from typing import Any

from prereg.runner import run_in_sandbox
from prereg.schema import AnalysisPlan, Check, RunResult, Verification

SCRIPTS = Path(__file__).resolve().parent / "sandbox_scripts"
REL_TOL = 1e-4
ABS_TOL = 1e-9
MAX_CATEGORIES = 20


def validate_plan(plan: AnalysisPlan, profile: dict) -> list[str]:
    """Problems that make the plan impossible to run on this data. Empty list means valid."""
    cols = {c["name"]: c for c in profile["columns"]}
    problems = [f"column {c!r} does not exist" for c in (plan.outcome, plan.predictor) if c not in cols]
    if problems:
        return problems
    if plan.outcome == plan.predictor:
        return ["outcome and predictor must be different columns"]
    y, x = cols[plan.outcome], cols[plan.predictor]
    problems += [f"{c['name']!r} has fewer than 2 distinct values" for c in (y, x) if c["unique"] < 2]
    if problems:
        return problems
    if plan.test in ("welch_t", "mann_whitney"):
        if y["kind"] != "numeric":
            problems.append(f"{plan.test} needs a numeric outcome; {y['name']!r} is categorical")
        if x["unique"] != 2:
            problems.append(f"{plan.test} needs a predictor with exactly 2 groups; {x['name']!r} has {x['unique']}")
    elif plan.test == "chi_square":
        problems += [
            f"chi_square needs at most {MAX_CATEGORIES} categories; {c['name']!r} has {c['unique']}"
            for c in (y, x) if c["unique"] > MAX_CATEGORIES
        ]
    elif plan.test == "ols":
        problems += [f"ols needs numeric columns; {c['name']!r} is categorical" for c in (y, x) if c["kind"] != "numeric"]
    return problems


def _close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def _number(result: dict, key: str) -> float | None:
    value = result.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        return None
    return float(value)


def _statistic_matches(test: str, claimed: float, truth: dict) -> bool:
    if _close(claimed, truth["statistic"]):
        return True
    if test == "welch_t":  # group order only flips the sign
        return _close(-claimed, truth["statistic"])
    if test == "mann_whitney":  # group order gives U or u_max - U
        return _close(truth["u_max"] - claimed, truth["statistic"])
    return False


def compare(plan: AnalysisPlan, claimed: dict[str, Any], truth: dict[str, Any]) -> Verification:
    """Pure comparison of the agent's result.json with the trusted recomputation."""
    stat, p = _number(claimed, "statistic"), _number(claimed, "p_value")
    decision = claimed.get("decision")
    checks = [
        Check(
            name="Result is complete",
            passed=stat is not None and p is not None and decision in ("reject", "fail_to_reject"),
            detail="statistic, p_value and decision present"
            if stat is not None and p is not None and decision in ("reject", "fail_to_reject")
            else "statistic or p_value is missing or not finite, or decision is not reject/fail_to_reject",
        ),
        Check(
            name="Ran the pre-registered test",
            passed=claimed.get("test") == plan.test,
            detail=f"plan says {plan.test}, result says {claimed.get('test')!r}",
        ),
    ]
    if stat is not None:
        checks.append(Check(
            name="Statistic reproduces",
            passed=_statistic_matches(plan.test, stat, truth),
            detail=f"agent {stat:.6g} vs independent {truth['statistic']:.6g}",
        ))
    if p is not None:
        checks.append(Check(
            name="p-value reproduces",
            passed=_close(p, truth["p_value"]),
            detail=f"agent {p:.6g} vs independent {truth['p_value']:.6g}",
        ))
        expected = "reject" if truth["p_value"] < plan.alpha else "fail_to_reject"
        checks.append(Check(
            name="Decision follows the pre-registered rule",
            passed=decision == expected,
            detail=f"p = {truth['p_value']:.4g} vs alpha = {plan.alpha} means {expected}; agent said {decision!r}",
        ))
    return Verification(passed=all(c.passed for c in checks), checks=tuple(checks), recomputed=truth)


def recompute_in_sandbox(plan: AnalysisPlan, csv_path: Path, on_line: Callable[[str], None] | None = None) -> RunResult:
    files = {
        "recompute.py": (SCRIPTS / "recompute.py").read_bytes(),
        "plan.json": json.dumps(plan.model_dump()).encode(),
    }
    return run_in_sandbox(csv_path, files, "recompute.py", on_line=on_line)


def profile_in_sandbox(csv_path: Path, on_line: Callable[[str], None] | None = None) -> RunResult:
    files = {"profile_csv.py": (SCRIPTS / "profile_csv.py").read_bytes()}
    return run_in_sandbox(csv_path, files, "profile_csv.py", on_line=on_line)
