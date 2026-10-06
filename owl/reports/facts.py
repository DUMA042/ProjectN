"""Server-side fact packs: exact aggregates over FULL files, model-ready text.

The model can never see raw rows (input budget + privacy), and profile
samples cannot support comparisons. So every figure the report may need is
computed here with pandas and rendered as compact text: cross-tabs by
department/grade/sex, time trends, rankings, and histogram bins. The model
narrates these exact numbers — it never estimates from samples.
"""
from __future__ import annotations

import io
from typing import Any

import pandas as pd

from owl.reports.profile import DATE_HINT, grouping_dimension

MAX_GROUPS = 12
MAX_BINS = 10
MAX_FACT_CHARS = 3500


def _read(csv_text: str) -> pd.DataFrame:
    return pd.read_csv(io.StringIO(csv_text.lstrip("\ufeff")), dtype=str).fillna("")


def _num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False), errors="coerce")


def _pct(n: float, d: float) -> str:
    if d <= 0:
        return "n/a"
    return f"{100.0 * n / d:.1f}% ({int(n):,} of {int(d):,})"


def cross_tab(df: pd.DataFrame, group_col: str, value_col: str | None = None) -> list[dict[str, Any]]:
    """Counts (and share) per group, or per-group mean for a numeric column."""
    g = df[group_col].astype(str).str.strip()
    g = g.where(g != "", "Unknown")
    if value_col is None:
        counts = g.value_counts()
        total = int(counts.sum())
        return [
            {"group": str(k), "count": int(v), "share": _pct(v, total)}
            for k, v in counts.head(MAX_GROUPS).items()
        ]
    nums = _num(df[value_col])
    out = []
    for k, idx in g.groupby(g).groups.items():
        vals = nums.loc[list(idx)].dropna()
        if vals.empty:
            continue
        out.append({"group": str(k), "count": int(vals.count()),
                    "mean": round(float(vals.mean()), 2)})
    out.sort(key=lambda r: -r["count"])
    return out[:MAX_GROUPS]


def trend(df: pd.DataFrame, date_col: str, freq: str = "M") -> list[dict[str, Any]]:
    """Row counts per month (M) or week (W)."""
    dates = pd.to_datetime(df[date_col].astype(str).str.slice(0, 10), errors="coerce")
    valid = dates.dropna()
    if valid.empty:
        return []
    key = valid.dt.to_period("M" if freq == "M" else "W").astype(str)
    counts = key.value_counts().sort_index()
    prev = None
    out = []
    for k, v in counts.items():
        row: dict[str, Any] = {"period": str(k), "count": int(v)}
        if prev:
            row["change_pct"] = round(100.0 * (v - prev) / prev, 1) if prev else 0.0
        prev = int(v)
        out.append(row)
    return out


def histogram_bins(df: pd.DataFrame, col: str) -> list[dict[str, Any]]:
    """Server-computed bins for a numeric column (model renders, never bins)."""
    vals = _num(df[col]).dropna()
    if vals.empty or vals.nunique() < 2:
        return []
    cats = pd.cut(vals, bins=min(MAX_BINS, max(2, vals.nunique())), precision=1)
    counts = cats.value_counts().sort_index()
    return [{"bin": str(k), "count": int(v)} for k, v in counts.items()]


def top_n(df: pd.DataFrame, col: str, n: int = 5) -> list[dict[str, Any]]:
    counts = df[col].astype(str).str.strip()
    counts = counts[counts != ""].value_counts().head(n)
    total = int(counts.sum())
    return [{"value": str(k), "count": int(v), "share": _pct(v, total)}
            for k, v in counts.items()]


def fact_pack(display_name: str, csv_text: str) -> dict[str, Any]:
    """One file -> exact aggregate facts (pure)."""
    try:
        df = _read(csv_text)
    except Exception:
        return {"file": display_name, "rows": 0, "error": "unreadable CSV"}
    if df.empty:
        return {"file": display_name, "rows": 0, "columns": list(df.columns)}
    cols = list(df.columns)
    groups = [(c, grouping_dimension(c)) for c in cols if grouping_dimension(c)]
    dates = [c for c in cols if DATE_HINT.search(c)]
    numerics = [c for c in cols if _num(df[c]).notna().sum() > 0]
    facts: dict[str, Any] = {"file": display_name, "rows": int(len(df))}
    if groups:
        by: dict[str, Any] = {}
        for col, dim in groups:
            by[dim] = cross_tab(df, col)
        facts["by_group"] = by
        # Department doubles as the mandatory comparison anchor.
        if "department" in by:
            facts["department_ranking"] = by["department"]
    if dates:
        spans = {}
        for c in dates[:3]:
            t = trend(df, c)
            if t:
                spans[c] = t
        if spans:
            facts["trends"] = spans
    if numerics:
        nums = {}
        for c in numerics[:6]:
            vals = _num(df[c]).dropna()
            if not vals.empty:
                nums[c] = {"min": round(float(vals.min()), 2),
                           "max": round(float(vals.max()), 2),
                           "mean": round(float(vals.mean()), 2),
                           "bins": histogram_bins(df, c)}
        if nums:
            facts["numerics"] = nums
    # Ranked values for the most informative categorical column.
    cat_cols = [c for c in cols if not grouping_dimension(c) and df[c].nunique() <= 20]
    if cat_cols:
        best = max(cat_cols, key=lambda c: df[c].nunique())
        facts["top_values"] = {best: top_n(df, best)}
    return facts


def render_facts(facts: list[dict[str, Any]]) -> str:
    """Fact packs -> prompt-sized text, hard-capped."""
    parts = []
    for f in facts:
        lines = [f"FACTS for {f['file']} ({f.get('rows', 0)} rows, EXACT — quote these):"]
        for dim, rows in (f.get("by_group") or {}).items():
            vals = "; ".join(
                f"{r['group']}: {r['count']}" + (f" ({r['share']})" if "share" in r else "")
                + (f" avg {r['mean']}" if "mean" in r else "")
                for r in rows)
            lines.append(f"  by {dim}: {vals}"[:400])
        for col, t in (f.get("trends") or {}).items():
            vals = "; ".join(
                f"{r['period']}: {r['count']}" + (f" ({r['change_pct']:+.1f}%)" if "change_pct" in r else "")
                for r in t)
            lines.append(f"  trend {col}: {vals}"[:300])
        for col, n in (f.get("numerics") or {}).items():
            lines.append(f"  numeric {col}: min {n['min']}, max {n['max']}, mean {n['mean']}")
            if n.get("bins"):
                lines.append("    bins: " + "; ".join(
                    f"{b['bin']}: {b['count']}" for b in n["bins"])[:250])
        for col, rows in (f.get("top_values") or {}).items():
            lines.append("  top " + col + ": " + "; ".join(
                f"{r['value']} {r['count']} ({r['share']})" for r in rows)[:300])
        parts.append("\n".join(lines))
    pack = "\n".join(parts)
    if len(pack) > MAX_FACT_CHARS:
        pack = pack[:MAX_FACT_CHARS] + "\n[truncated]"
    return pack
