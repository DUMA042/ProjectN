"""Compact CSV profiler for the AI analysis pass.

The model can never receive raw files (6k-char input budget, and raw rows
must stay server-side). Each file is reduced to a profile pack: schema,
row counts, numeric summaries, low-cardinality distributions, date spans,
and a few sample rows. Profiles are capped so the whole pack fits the budget.
"""
from __future__ import annotations

import csv
import io
import re
from datetime import date
from typing import Any

MAX_COLS = 20
MAX_TOP_VALUES = 8
MAX_SAMPLE_ROWS = 3
MAX_CELL_CHARS = 60
MAX_PACK_CHARS = 5000

DATE_HINT = re.compile(r"date|day|month|year|period", re.IGNORECASE)

# Normalized column names that define HR grouping dimensions. Equality match
# only (same discipline as ID/NAME headers): "departmentname" matches, but a
# bare "code" or "group" column never does.
GROUPING_DIMENSIONS = {
    "department": "department",
    "departmentname": "department",
    "dept": "department",
    "grade": "grade level",
    "gradelevel": "grade level",
    "rank": "rank",
    "sex": "sex",
    "gender": "sex",
    "employmentstatus": "employment status",
    "employmenttype": "employment type",
    "location": "location",
    "worklocation": "location",
}


def grouping_dimension(header: str) -> str | None:
    """HR grouping dimension for a column header, or None."""
    return GROUPING_DIMENSIONS.get(re.sub(r"[\s_]+", "", str(header).strip().lower()))


def _short(value: object) -> str:
    s = str(value).strip() if value is not None else ""
    return s if len(s) <= MAX_CELL_CHARS else s[:MAX_CELL_CHARS] + "…"


def _try_float(value: str) -> float | None:
    try:
        return float(value.replace(",", "").strip())
    except (ValueError, AttributeError):
        return None


def _try_date(value: str) -> date | None:
    s = value.strip()[:10]
    try:
        y, m, d = int(s[0:4]), int(s[5:7]), int(s[8:10])
        return date(y, m, d)
    except (ValueError, IndexError):
        return None


def profile_csv(display_name: str, csv_text: str) -> dict[str, Any]:
    """One file -> compact profile dict (pure, no I/O)."""
    reader = csv.reader(io.StringIO(csv_text.lstrip("\ufeff")))
    rows = list(reader)
    if not rows:
        return {"file": display_name, "rows": 0, "columns": []}
    header, body = rows[0], rows[1:]
    cols = header[:MAX_COLS]
    n = len(cols)
    numeric: list[dict[str, Any]] = [{} for _ in range(n)]
    for i in range(n):
        vals = [_try_float(r[i]) for r in body if i < len(r) and r[i].strip()]
        nums = [v for v in vals if v is not None]
        numeric[i] = {
            "numeric_count": len(nums),
            "min": round(min(nums), 2) if nums else None,
            "max": round(max(nums), 2) if nums else None,
        }
    cat: list[list[tuple[str, int]]] = [[] for _ in range(n)]
    for i in range(n):
        counts: dict[str, int] = {}
        for r in body:
            v = r[i].strip() if i < len(r) else ""
            if v:
                counts[v] = counts.get(v, 0) + 1
        # Skip high-cardinality columns (IDs, tokens, free text): top-N would
        # be noise and could leak token-shaped values into the prompt.
        if 0 < len(counts) <= MAX_TOP_VALUES + 4:
            top = sorted(counts.items(), key=lambda kv: -kv[1])[:MAX_TOP_VALUES]
            cat[i] = [(k, c) for k, c in top]
    dates: list[dict[str, str]] = [{} for _ in range(n)]
    for i, h in enumerate(cols):
        if not DATE_HINT.search(h):
            continue
        ds = [_try_date(r[i]) for r in body if i < len(r) and r[i].strip()]
        ds = [d for d in ds if d is not None]
        if ds:
            dates[i] = {"from": min(ds).isoformat(), "to": max(ds).isoformat()}
    return {
        "file": display_name,
        "rows": len(body),
        "columns": [
            {
                "name": h,
                "numeric": numeric[i]["numeric_count"] > 0,
                "min": numeric[i]["min"],
                "max": numeric[i]["max"],
                "top_values": [{"value": _short(k), "count": c} for k, c in cat[i]],
                **({"date_span": dates[i]} if dates[i] else {}),
                **({"grouping": grouping_dimension(h)} if grouping_dimension(h) else {}),
            }
            for i, h in enumerate(cols)
        ],
        "sample_rows": [
            [_short(r[i]) if i < len(r) else "" for i in range(n)]
            for r in body[:MAX_SAMPLE_ROWS]
        ],
    }


def pack_profiles(profiles: list[dict[str, Any]]) -> str:
    """Profiles -> prompt-sized text, hard-capped at MAX_PACK_CHARS."""
    parts: list[str] = []
    for p in profiles:
        lines = [f"FILE: {p['file']} ({p['rows']} rows)"]
        for c in p["columns"]:
            bits = [c["name"]]
            if c.get("grouping"):
                bits.append(f"GROUPING:{c['grouping']}")
            if c.get("date_span"):
                ds = c["date_span"]
                bits.append(f"dates {ds['from']}..{ds['from']}" if ds["from"] == ds["to"]
                            else f"dates {ds['from']}..{ds['to']}")
            if c["numeric"] and c["min"] is not None:
                bits.append(f"numeric {c['min']}..{c['max']}")
            for t in c["top_values"]:
                bits.append(f"{t['value']}×{t['count']}")
            col_line = " | ".join(bits)
            lines.append("  - " + (col_line[:140]))
        if p["sample_rows"]:
            lines.append("  sample: " + "; ".join(" | ".join(r) for r in p["sample_rows"])[:300])
        parts.append("\n".join(lines))
    pack = "\n".join(parts)
    return pack if len(pack) <= MAX_PACK_CHARS else pack[:MAX_PACK_CHARS] + "\n[truncated]"
