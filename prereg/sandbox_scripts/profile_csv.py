"""Trusted profiler. Runs inside the sandbox, so even reading the upload never happens on the host.

Usage: python profile_csv.py [csv_path] [out_path]
"""

import json
import re
import sys

import matplotlib
import numpy
import pandas as pd
import scipy
import statsmodels

CSV = sys.argv[1] if len(sys.argv) > 1 else "/data/input.csv"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/out/result.json"
MAX_COLUMNS = 50
SAMPLE_ROWS = 5
MAX_CELL_CHARS = 200
SUSPICIOUS = re.compile(
    r"ignore (all |any )?(previous|prior|above) instructions|os\.environ|environment variables|"
    r"\b(curl|wget)\b|https?://|api[_ ]?key|secret|exfiltrat|subprocess|socket\.",
    re.IGNORECASE,
)


def column_profile(series: pd.Series) -> dict:
    numeric = pd.api.types.is_numeric_dtype(series)
    info = {
        "name": str(series.name),
        "kind": "numeric" if numeric else "categorical",
        "missing": int(series.isna().sum()),
        "unique": int(series.nunique(dropna=True)),
    }
    if numeric:
        desc = series.describe()
        info.update({k: round(float(desc[k]), 4) for k in ("mean", "std", "min", "max") if pd.notna(desc.get(k))})
    else:
        top = series.astype(str).value_counts().head(6)
        info["top_values"] = {str(k)[:MAX_CELL_CHARS]: int(v) for k, v in top.items()}
    return info


def find_suspicious(df: pd.DataFrame) -> list[dict]:
    hits = []
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            continue
        for idx, val in df[col].dropna().astype(str).items():
            if SUSPICIOUS.search(val):
                hits.append({"row": int(idx) + 2, "column": str(col), "excerpt": val[:MAX_CELL_CHARS]})
            if len(hits) >= 10:
                return hits
    return hits


def main() -> None:
    print("profiler: reading", CSV)
    df = pd.read_csv(CSV)
    if df.shape[1] > MAX_COLUMNS:
        raise SystemExit(f"too many columns: {df.shape[1]} (limit {MAX_COLUMNS})")
    sample = df.head(SAMPLE_ROWS).astype(str).map(lambda v: v[:MAX_CELL_CHARS])
    profile = {
        "rows": int(df.shape[0]),
        "columns": [column_profile(df[c]) for c in df.columns],
        "sample": sample.to_dict(orient="records"),
        "suspicious": find_suspicious(df),
        "versions": {
            "python": sys.version.split()[0],
            "pandas": pd.__version__,
            "numpy": numpy.__version__,
            "scipy": scipy.__version__,
            "statsmodels": statsmodels.__version__,
            "matplotlib": matplotlib.__version__,
        },
    }
    with open(OUT, "w") as fh:
        json.dump(profile, fh)
    print(f"profiler: {profile['rows']} rows x {len(profile['columns'])} columns")
    if profile["suspicious"]:
        print(f"profiler: WARNING {len(profile['suspicious'])} cell(s) look like instructions, treated as data")


if __name__ == "__main__":
    main()
