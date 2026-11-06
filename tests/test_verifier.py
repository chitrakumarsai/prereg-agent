import json
import subprocess
import sys

import pandas as pd
import pytest
from conftest import ROOT, SANDBOX

from prereg.schema import AnalysisPlan
from prereg.verifier import SCRIPTS, compare, recompute_in_sandbox, validate_plan


def _plan(**overrides) -> AnalysisPlan:
    base = dict(hypothesis="Value differs by variant", test="welch_t", outcome="value", predictor="variant",
                alpha=0.05, decision_rule="Reject H0 if p < 0.05")
    return AnalysisPlan(**{**base, **overrides})


TRUTH = {"statistic": -2.5, "p_value": 0.013, "u_max": 100.0}


def test_valid_plan_has_no_problems(profile):
    assert validate_plan(_plan(), profile) == []


@pytest.mark.parametrize(
    ("overrides", "fragment"),
    [
        ({"outcome": "nope"}, "does not exist"),
        ({"outcome": "variant", "predictor": "value"}, "numeric outcome"),
        ({"predictor": "store"}, "exactly 2 groups"),
        ({"test": "ols", "predictor": "variant"}, "numeric columns"),
        ({"test": "chi_square", "outcome": "store"}, "at most 20"),
        ({"predictor": "value"}, "different columns"),
    ],
)
def test_invalid_plans_are_rejected(profile, overrides, fragment):
    assert any(fragment in p for p in validate_plan(_plan(**overrides), profile))


def test_matching_result_passes():
    claimed = {"test": "welch_t", "statistic": -2.5, "p_value": 0.013, "decision": "reject"}
    assert compare(_plan(), claimed, TRUTH).passed


def test_flipped_group_order_still_passes():
    claimed = {"test": "welch_t", "statistic": 2.5, "p_value": 0.013, "decision": "reject"}
    assert compare(_plan(), claimed, TRUTH).passed


def test_swapped_mann_whitney_u_passes():
    claimed = {"test": "mann_whitney", "statistic": 102.5, "p_value": 0.013, "decision": "reject"}
    assert compare(_plan(test="mann_whitney"), claimed, TRUTH).passed


@pytest.mark.parametrize(
    ("claimed", "failing"),
    [
        ({"test": "welch_t", "statistic": -2.5, "p_value": 0.2, "decision": "reject"}, "p-value reproduces"),
        ({"test": "welch_t", "statistic": -2.5, "p_value": 0.013, "decision": "fail_to_reject"},
         "Decision follows the pre-registered rule"),
        ({"test": "mann_whitney", "statistic": -2.5, "p_value": 0.013, "decision": "reject"},
         "Ran the pre-registered test"),
        ({"test": "welch_t", "statistic": 9.9, "p_value": 0.013, "decision": "reject"}, "Statistic reproduces"),
        ({"test": "welch_t", "statistic": "NaN", "p_value": True, "decision": "reject"}, "Result is complete"),
    ],
)
def test_wrong_results_fail_the_right_check(claimed, failing):
    verification = compare(_plan(), claimed, TRUTH)
    assert not verification.passed
    assert failing in {c.name for c in verification.checks if not c.passed}


def test_fingerprint_is_stable_and_sensitive():
    assert _plan().fingerprint() == _plan().fingerprint()
    assert _plan().fingerprint() != _plan(alpha=0.01).fingerprint()


@pytest.mark.parametrize("test", ["welch_t", "mann_whitney"])
def test_recompute_script_matches_scipy_on_host(tmp_path, test):
    csv = ROOT / "demo" / "checkout_ab_test.csv"
    plan = _plan(test=test, outcome="order_value_usd", predictor="variant")
    plan_path, out_path = tmp_path / "plan.json", tmp_path / "out.json"
    plan_path.write_text(json.dumps(plan.model_dump()))
    subprocess.run([sys.executable, str(SCRIPTS / "recompute.py"), str(plan_path), str(csv), str(out_path)], check=True)
    result = json.loads(out_path.read_text())
    df = pd.read_csv(csv)
    assert result["n_used"] == len(df)
    assert 0 <= result["p_value"] <= 1


@SANDBOX
def test_recompute_in_sandbox(demo_csv):
    plan = _plan(outcome="order_value_usd", predictor="variant")
    run = recompute_in_sandbox(plan, demo_csv)
    assert run.status == "ok", run.log
    assert run.result["groups"] == ["control", "one_page_checkout"]


def test_single_value_column_is_rejected(profile):
    one_value = {**profile, "columns": [*profile["columns"], {"name": "flat", "kind": "numeric", "unique": 1}]}
    problems = validate_plan(_plan(test="ols", outcome="value", predictor="flat"), one_value)
    assert any("fewer than 2 distinct values" in p for p in problems)
