"""Trusted, fixed recomputation of a pre-registered test. Never written by the model.

Reads the frozen plan from plan.json and recomputes the statistic with the canonical call
that the code-writing prompt also prescribes, so the two numbers must agree.

Usage: python recompute.py [plan_path] [csv_path] [out_path]
"""

import json
import sys

import pandas as pd
import statsmodels.api as sm
from scipy import stats

PLAN = sys.argv[1] if len(sys.argv) > 1 else "/code/plan.json"
CSV = sys.argv[2] if len(sys.argv) > 2 else "/data/input.csv"
OUT = sys.argv[3] if len(sys.argv) > 3 else "/out/result.json"


def two_groups(df: pd.DataFrame, outcome: str, predictor: str) -> tuple[pd.Series, pd.Series, list]:
    levels = sorted(df[predictor].unique(), key=str)
    if len(levels) != 2:
        raise SystemExit(f"{predictor!r} has {len(levels)} levels; this test needs exactly 2")
    a = df.loc[df[predictor] == levels[0], outcome].astype(float)
    b = df.loc[df[predictor] == levels[1], outcome].astype(float)
    return a, b, levels


def recompute(plan: dict, df: pd.DataFrame) -> dict:
    y, x, test = plan["outcome"], plan["predictor"], plan["test"]
    df = df[[y, x]].dropna()
    if test == "welch_t":
        a, b, levels = two_groups(df, y, x)
        res = stats.ttest_ind(a, b, equal_var=False)
        extra = {"groups": [str(l) for l in levels], "means": [float(a.mean()), float(b.mean())]}
        return {"statistic": float(res.statistic), "p_value": float(res.pvalue), "n_used": len(df), **extra}
    if test == "mann_whitney":
        a, b, levels = two_groups(df, y, x)
        res = stats.mannwhitneyu(a, b, alternative="two-sided")
        extra = {
            "groups": [str(l) for l in levels],
            "medians": [float(a.median()), float(b.median())],
            "u_max": float(len(a) * len(b)),  # U and u_max - U are the same test with groups swapped
        }
        return {"statistic": float(res.statistic), "p_value": float(res.pvalue), "n_used": len(df), **extra}
    if test == "chi_square":
        chi2, p, dof, _ = stats.chi2_contingency(pd.crosstab(df[y], df[x]))
        return {"statistic": float(chi2), "p_value": float(p), "n_used": len(df), "dof": int(dof)}
    if test == "ols":
        model = sm.OLS(df[y].astype(float), sm.add_constant(df[x].astype(float))).fit()
        return {
            "statistic": float(model.tvalues[x]),
            "p_value": float(model.pvalues[x]),
            "n_used": len(df),
            "coefficient": float(model.params[x]),
            "r_squared": float(model.rsquared),
        }
    raise SystemExit(f"unsupported test {test!r}")


def main() -> None:
    with open(PLAN) as fh:
        plan = json.load(fh)
    print(f"verifier: independently recomputing {plan['test']} on {plan['outcome']} by {plan['predictor']}")
    result = recompute(plan, pd.read_csv(CSV))
    with open(OUT, "w") as fh:
        json.dump(result, fh)
    print(f"verifier: statistic={result['statistic']:.6g} p={result['p_value']:.6g}")


if __name__ == "__main__":
    main()
