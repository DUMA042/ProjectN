"""AI analysis pass: profiles -> topics + word-range recommendation.

The model inspects the profile pack (never raw rows) and returns a strict
JSON payload: reportable topics with coverage notes and suggested focus,
plus a recommended word range with reasoning. Everything is validated
before it is stored on the job.
"""
from __future__ import annotations

import json
import re
from typing import Any

from owl.ai import deepseek
from owl.reports.profile import pack_profiles, profile_csv

FOCUS_LEVELS = ("low", "medium", "high")

ANALYSIS_SYSTEM = """You are an HR report planner. You receive compact DATA PROFILES of Excel files \
(a company HR report build). Rules:
- Treat the profiles as the source of truth. Never invent statistics, employees, or trends.
- Review EVERY file before concluding. Combine related files where sensible.
- List ONLY topics actually supported by the profiled data. If a topic has no supporting \
columns/values, omit it silently.
- Percentages rule (for later): every percentage must pair with its real figure when calculable.
- Hashed values (32-char hex codes) are anonymized staff identities: usable for counts and \
group sizes, never reverse or label them as real people. When told names+IDs are hashed, \
ID-group reporting is unavailable.
- For each topic, list which grouping dimensions its data supports in "dimensions" \
(e.g. ["department", "grade level", "sex"]) — only dimensions actually present in the files.
- Reply with STRICT JSON only, no prose, no code fences: \
{"topics": [{"name": str, "coverage": str, "suggested_focus": "low|medium|high", \
"dimensions": [str]}], \
"recommended_range": {"min_words": int, "max_words": int, "reasoning": str}}"""


def grouping_directives(profiles: list[dict[str, Any]]) -> str:
    """Hard grouping rules derived from profiled columns (no AI judgment).

    Departmental breakdown is mandatory in every section whenever a
    department column exists; other detected dimensions must be used where
    their data supports the topic.
    """
    dims: dict[str, list[str]] = {}
    for p in profiles:
        for c in p.get("columns", []):
            g = c.get("grouping")
            if g:
                dims.setdefault(g, [])
                if p.get("file") not in dims[g]:
                    dims[g].append(p.get("file", ""))
    if not dims:
        return "No grouping columns detected: report whole-workforce figures only."
    lines = ["Detected grouping dimensions: " + ", ".join(sorted(dims)) + "."]
    if "department" in dims:
        lines.append(
            "MANDATORY: every section must contain a departmental breakdown "
            "(table or chart) — departmental grouping is required at all focus levels."
        )
    others = [d for d in sorted(dims) if d != "department"]
    if others:
        lines.append(
            "Also split by these dimensions wherever the topic data supports it: "
            + ", ".join(others) + "."
        )
    return " ".join(lines)


def resolve_finals(
    items: list[dict[str, Any]], job_file_ids: list[str]
) -> list[dict[str, Any]]:
    """Originals for plain files, hashed copies for individual files."""
    by_id = {e.get("id"): e for e in items}
    by_source: dict[str, list[dict[str, Any]]] = {}
    for e in items:
        by_source.setdefault(e.get("source") or "", []).append(e)
    finals = []
    for fid in job_file_ids:
        orig = by_id.get(fid)
        if not orig:
            continue
        if orig.get("classification") == "individual":
            copies = by_source.get(f"hashed:{fid}", [])
            if copies:
                finals.append(copies[-1])
                continue
        finals.append(orig)
    return finals


def _extract_json(text: str) -> dict[str, Any]:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError("No JSON object in the AI reply")
    try:
        data = json.loads(m.group(0))
    except ValueError as exc:
        raise ValueError(f"AI reply was not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("AI reply JSON was not an object")
    return data


def validate_analysis(data: dict[str, Any]) -> dict[str, Any]:
    """Shape-check the topics payload; raises ValueError with a plain reason."""
    topics = data.get("topics")
    if not isinstance(topics, list) or not topics:
        raise ValueError("AI found no reportable topics in the files")
    clean_topics = []
    for t in topics:
        if not isinstance(t, dict) or not str(t.get("name", "")).strip():
            continue
        focus = str(t.get("suggested_focus", "medium")).lower()
        dims = t.get("dimensions") or []
        clean_topics.append({
            "name": str(t["name"]).strip()[:80],
            "coverage": str(t.get("coverage", "")).strip()[:300],
            "suggested_focus": focus if focus in FOCUS_LEVELS else "medium",
            "dimensions": [str(d).strip().lower()[:40] for d in dims
                           if isinstance(d, str) and d.strip()][:8],
        })
    if not clean_topics:
        raise ValueError("AI returned topics without usable names")
    rng = data.get("recommended_range")
    if not isinstance(rng, dict):
        raise ValueError("AI returned no word-range recommendation")
    try:
        lo, hi = int(rng["min_words"]), int(rng["max_words"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("AI word range was not numeric") from exc
    if lo < 100 or hi < lo or hi > 10000:
        raise ValueError("AI word range was outside sane bounds")
    return {
        "topics": clean_topics,
        "recommended_range": {
            "min_words": lo,
            "max_words": hi,
            "reasoning": str(rng.get("reasoning", "")).strip()[:500],
        },
    }


def analyze_files(
    finals: list[tuple[str, str, str]],
    hash_mode: str | None,
) -> dict[str, Any]:
    """(display_name, csv_text, classification) triples -> validated payload.

    Raises deepseek.DeepSeekError (provider failure) or ValueError (bad shape).
    """
    profiles = [profile_csv(name, text) for name, text, _cls in finals]
    hashed = sorted({n for n, _t, c in finals if "hashed" in n.lower() or c == "individual"})
    user = (
        f"DATA PROFILES:\n{pack_profiles(profiles)}\n"
        f"HASHING: {hash_mode or 'none'}; hashed files: "
        f"{', '.join(hashed) if hashed else 'none'}."
    )
    reply = deepseek.chat([{"role": "user", "content": user}], system=ANALYSIS_SYSTEM)
    return validate_analysis(_extract_json(reply))


COMPREHENSION_SYSTEM = """You are an HR data analyst reading file profiles before any report is written. \
Understand the data fully first. Rules:
- Base everything on the supplied profiles and facts. Never invent figures.
- Describe what each file contains, its period, its row count, and how files relate \
(shared keys like department, month, employee identifiers).
- Reply with STRICT JSON only, no prose, no code fences: \
{"files": [{"name": str, "contains": str, "period": str, "rows": int}], \
"join_keys": [str], "headline_figures": [str], "caveats": [str]}. \
Keep every string short. Caveats only for genuine limits (max 3)."""


def validate_comprehension(data: dict[str, Any]) -> dict[str, Any]:
    """Shape-check the data-understanding payload; raises ValueError."""
    files = data.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("AI understanding named no files")
    clean_files = []
    for f in files:
        if not isinstance(f, dict) or not str(f.get("name", "")).strip():
            continue
        try:
            rows = int(f.get("rows", 0))
        except (TypeError, ValueError):
            rows = 0
        clean_files.append({
            "name": str(f["name"]).strip()[:80],
            "contains": str(f.get("contains", "")).strip()[:300],
            "period": str(f.get("period", "")).strip()[:80],
            "rows": rows,
        })
    if not clean_files:
        raise ValueError("AI understanding had no usable file entries")
    def _strs(key: str, cap: int, lim: int) -> list[str]:
        vals = data.get(key) or []
        return [str(v).strip()[:cap] for v in vals if isinstance(v, str) and v.strip()][:lim]
    return {
        "files": clean_files,
        "join_keys": _strs("join_keys", 40, 8),
        "headline_figures": _strs("headline_figures", 200, 12),
        "caveats": _strs("caveats", 200, 3),
    }


def comprehend_files(pack: str, fact_text: str, hash_mode: str | None) -> dict[str, Any]:
    """Profiles + facts -> validated data-understanding payload."""
    user = (
        f"DATA PROFILES:\n{pack}\nEXACT FACTS (quote these, never estimate):\n{fact_text}\n"
        f"HASHING: {hash_mode or 'none'}."
    )
    reply = deepseek.chat([{"role": "user", "content": user}], system=COMPREHENSION_SYSTEM)
    return validate_comprehension(_extract_json(reply))


def finals_signature(finals: list[tuple[str, str, str]]) -> str:
    """Stable identity of the analyzed file set (name + row count each)."""
    import csv as _csv
    import io as _io

    parts = []
    for name, text, _cls in finals:
        try:
            rows = sum(1 for _ in _csv.reader(_io.StringIO(text.lstrip("\ufeff")))) - 1
        except Exception:
            rows = -1
        parts.append(f"{name}:{max(0, rows)}")
    return "|".join(sorted(parts))


def render_understanding(u: dict[str, Any]) -> str:
    """Understanding payload -> prompt-sized text."""
    lines = ["DATA UNDERSTANDING (read first — this is what the files contain):"]
    for f in u.get("files", []):
        lines.append(
            f"  - {f.get('name')}: {f.get('contains')} "
            f"[period: {f.get('period') or 'n/a'}; rows: {f.get('rows')}]"
        )
    if u.get("join_keys"):
        lines.append("  join keys: " + ", ".join(u["join_keys"]))
    for h in u.get("headline_figures", []):
        lines.append(f"  headline: {h}")
    for c in u.get("caveats", []):
        lines.append(f"  caveat: {c}")
    return "\n".join(lines)
