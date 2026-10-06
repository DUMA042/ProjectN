"""LLM Narration Layer + provenance gate.

Provenance rule (locked): a sensitive value may enter the narration payload
IFF its normalized form appears in the user's own question text (the user
typed it). All other sensitive values become stable-per-batch placeholders
([NAME-1], [ID-1], ...) substituted server-side after narration.

The authoritative UI table always renders real values from the result
contract — narration is descriptive only and the app works without it.
"""
from __future__ import annotations

import json

from owl.ai import deepseek

PLACEHOLDER_KIND = {
    "full_name": "NAME",
    "id_no": "ID",
    "employee_id": "ID",
    "phone_number": "PHONE",
    "sex": "SEX",
    "employment_status": "STATUS",
}

NARRATE_SYSTEM = (
    "Your name is BLUE. Narrate the FINDINGS below for an HR manager in 2-4 sentences. "
    "Identifiers appear as opaque placeholders like [NAME-1] — repeat them EXACTLY, "
    "never invent or expand them. Only use numbers present in FINDINGS. "
    "No markdown tables, no extra formatting."
)


def normalize(value: object) -> str:
    return " ".join(str(value).split()).casefold()


def _expr_fields(node: dict, out: set[str]) -> None:
    if not isinstance(node, dict):
        return
    if set(node.keys()) == {"field"} and isinstance(node.get("field"), str):
        out.add(node["field"])
    for a in node.get("args", []) or []:
        if isinstance(a, dict):
            _expr_fields(a, out)


def _tier_of(field: str, entity_fields: dict) -> str:
    return entity_fields.get(field, {}).get("visibility", "sensitive")


def output_tiers(ir: dict, entity_fields: dict) -> dict[str, str]:
    """Output-column name -> tier for one entity's fields.

    Aggregates over sensitive bases stay sensitive unless they are pure
    counts; expressions inherit sensitivity from any referenced sensitive
    field; unknown fields fail closed to sensitive.
    """
    tiers: dict[str, str] = {}
    for item in ir.get("select", []) or []:
        if not isinstance(item, dict):
            continue
        if "aggregate" in item:
            base_fields: set[str] = set()
            if isinstance(item.get("field"), str):
                base_fields.add(item["field"])
            if isinstance(item.get("expression"), dict):
                _expr_fields(item["expression"], base_fields)
            sens = any(_tier_of(f, entity_fields) == "sensitive" for f in base_fields)
            tiers[item["alias"]] = (
                "sensitive" if (sens and item["aggregate"] not in ("COUNT", "COUNT DISTINCT"))
                else "public"
            )
        elif "expression" in item or "case" in item:
            refs: set[str] = set()
            if isinstance(item.get("expression"), dict):
                _expr_fields(item["expression"], refs)
            case = item.get("case")
            if isinstance(case, dict):
                for w in case.get("whens", []) or []:
                    if isinstance(w, dict):
                        _filter_refs(w.get("when", {}), refs)
            tiers[item["alias"]] = (
                "sensitive" if any(_tier_of(f, entity_fields) == "sensitive" for f in refs) else "public"
            )
        elif "field" in item:
            name = item.get("alias") or item["field"]
            tiers[name] = _tier_of(item["field"], entity_fields)
    return tiers


def _filter_refs(node: dict, out: set[str]) -> None:
    if not isinstance(node, dict):
        return
    if "and" in node or "or" in node:
        for k in node.get("and", node.get("or", [])) or []:
            _filter_refs(k, out)
        return
    if "not" in node:
        _filter_refs(node["not"], out)
        return
    if isinstance(node.get("field"), str):
        out.add(node["field"])


def prepare(question: str, rows: list[dict], sensitive_cols: set[str]) -> tuple[list[dict], dict[str, str]]:
    """Split rows into narration-safe payload + substitution map.

    Sensitive cells pass through ONLY when the user typed the value
    themselves (normalized containment in the question).
    """
    qnorm = f" {normalize(question)} "
    counters: dict[str, int] = {}
    seen: dict[tuple[str, str], str] = {}
    sub_map: dict[str, str] = {}

    def placeholder(field: str, value: object) -> str:
        kind = PLACEHOLDER_KIND.get(field, "VAL")
        key = (kind, str(value))
        if key not in seen:
            counters[kind] = counters.get(kind, 0) + 1
            token = f"[{kind}-{counters[kind]}]"
            seen[key] = token
            sub_map[token] = str(value)
        return seen[key]

    payload: list[dict] = []
    for r in rows:
        row: dict = {}
        for k, v in r.items():
            if v is None:
                row[k] = ""
            elif k in sensitive_cols and f" {normalize(v)} " not in qnorm:
                row[k] = placeholder(k, v)
            else:
                row[k] = v
        payload.append(row)
    return payload, sub_map


def substitute(text: str, sub_map: dict[str, str]) -> str:
    """Restore real values into narrated prose (server-side, post-model)."""
    for token, real in sub_map.items():
        text = text.replace(token, real)
    return text


def fallback_text(row_count: int) -> str:
    return (
        f"I found {row_count} matching row{'s' if row_count != 1 else ''} — "
        "see the results table below for the full breakdown."
    )


def _t_top_early(rows: list[dict], period: str | None) -> str:
    head = f"Top {len(rows)} early arrivals" + (f" ({period})" if period else "") + ":"
    lines = [head]
    for i, r in enumerate(rows, 1):
        lines.append(f"{i}. {r.get('full_name')} ({r.get('checkin_time')})")
    return "\n".join(lines)


def _t_on_leave(rows: list[dict], period: str | None) -> str:
    head = f"Staff on leave" + (f" ({period})" if period else "")
    if not rows:
        return f"No staff on leave recorded{(' for ' + period) if period else ''}."
    lines = [f"{head}: {len(rows)}"]
    for r in rows:
        span = f"{r.get('start_date')} to {r.get('end_date')}" if r.get("end_date") else str(r.get("start_date"))
        lines.append(f"- {r.get('full_name')} ({span})")
    return "\n".join(lines)


def _t_top_absent(rows: list[dict], period: str | None) -> str:
    head = "Highest unexcused absence" + (f" ({period})" if period else "")
    lines = [head + ":"]
    for i, r in enumerate(rows, 1):
        lines.append(f"{i}. {r.get('full_name')} — {r.get('absent_days')} days absent")
    return "\n".join(lines)


def _t_late(rows: list[dict], period: str | None) -> str:
    head = "Latest arrivals" + (f" ({period})" if period else "")
    lines = [head + ":"]
    for i, r in enumerate(rows, 1):
        lines.append(f"{i}. {r.get('full_name')} — {r.get('checkin_time')}")
    return "\n".join(lines)


def _t_late_checkouts(rows: list[dict], period: str | None) -> str:
    head = "Latest checkouts" + (f" ({period})" if period else "")
    lines = [head + ":"]
    for i, r in enumerate(rows, 1):
        lines.append(f"{i}. {r.get('full_name')} — {r.get('checkout_time')}")
    return "\n".join(lines)


def _t_dept_rate(rows: list[dict], period: str | None) -> str:
    head = "Department attendance rates" + (f" ({period})" if period else "")
    lines = [head + ":"]
    for r in rows:
        try:
            rate = 100.0 * float(r.get("present_days") or 0) / float(r.get("expected_days") or 1)
        except (TypeError, ValueError, ZeroDivisionError):
            rate = 0.0
        lines.append(f"- {r.get('department')}: {rate:.1f}%")
    return "\n".join(lines)


def _t_top_hours(rows: list[dict], period: str | None) -> str:
    head = "Most working hours" + (f" ({period})" if period else "")
    lines = [head + ":"]
    for i, r in enumerate(rows, 1):
        try:
            hrs = float(r.get("total_minutes") or 0) / 60.0
        except (TypeError, ValueError):
            hrs = 0.0
        lines.append(f"{i}. {r.get('full_name')} — {hrs:.1f} hours")
    return "\n".join(lines)


TEMPLATES = {
    "top_early": _t_top_early,
    "on_leave": _t_on_leave,
    "top_absent": _t_top_absent,
    "late_comers": _t_late,
    "late_checkouts": _t_late_checkouts,
    "dept_rate": _t_dept_rate,
    "top_hours": _t_top_hours,
}


def render(template: str | None, rows: list[dict], period: str | None) -> str | None:
    """Deterministic narration for known shapes; None -> caller uses the model."""
    fn = TEMPLATES.get(template or "")
    if fn is None:
        return None
    return fn(rows, period)


def narrate(question: str, payload_rows: list[dict], transport=None) -> str:
    """Model narration over sanitized findings; template fallback on failure."""
    facts = payload_rows[:20]
    prompt = (
        f"QUESTION: {question}\n"
        "FINDINGS (placeholders are opaque IDs, repeat exactly): "
        f"{json.dumps(facts, default=str)[:4000]}"
    )
    try:
        return deepseek.chat([{"role": "user", "content": prompt}], system=NARRATE_SYSTEM, transport=transport)
    except deepseek.DeepSeekError:
        return fallback_text(len(payload_rows))
