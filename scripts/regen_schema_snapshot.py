"""Regenerate owl/ai/snapshot.json — the reviewed static knowledge for BLUE.

Contains ONLY non-employee information: schema metadata (table/column names),
rule settings, dimension definitions, and the intent vocabulary. NEVER row
data. Review the diff before committing: this file is what the model sees.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

from owl.load.database import get_session
from owl.rules.engine import get_rule

# Tables the query engine may touch (allowlist mirrors the compiler).
SNAPSHOT_TABLES = [
    "employees",
    "attendance_daily",
    "leave_records",
    "employee_trainings",
    "departments",
    "grade_levels",
    "ranks",
    "employment_types",
    "employee_statuses",
    "leave_types",
    "locations",
    "venues",
    "consultants",
]

RULE_KEYS = [
    "working_hours",
    "holidays",
    "incomplete_threshold",
    "eligible_statuses",
    "leave_overrides_training",
]

INTENTS = [
    "top_early",
    "on_leave",
    "top_absent",
    "late_comers",
    "dept_rate",
    "rule_lookup",
]

DEFINITIONS = {
    "absent": "Past working day with no swipe and no leave/training logged, for an employee whose status is eligible.",
    "attendance_rate": "Present staff-days divided by expected staff-days (percent).",
    "incomplete_day": "First-to-last swipe gap under the incomplete threshold (default 1 hour).",
    "working_day": "Configured weekday (working_hours) that is not a holiday.",
    "leave_overrides_training": "When leave and training overlap a day, leave wins (configurable).",
}


def build() -> dict:
    with get_session() as s:
        cols = s.execute(
            text(
                "SELECT table_name, column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' ORDER BY table_name, ordinal_position"
            )
        ).mappings().all()
    tables = {}
    for r in cols:
        if r["table_name"] in SNAPSHOT_TABLES:
            tables.setdefault(r["table_name"], []).append(r["column_name"])
    rules = {k: get_rule(k, {}) for k in RULE_KEYS}
    try:
        from owl.analytics.dimensions import DIMENSIONS

        dimensions = {k: v.get("label", k) for k, v in DIMENSIONS.items()}
    except Exception:
        dimensions = {}
    return {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tables": tables,
        "rules": rules,
        "dimensions": dimensions,
        "intents": INTENTS,
        "definitions": DEFINITIONS,
    }


def main() -> None:
    out = Path(__file__).resolve().parent.parent / "owl" / "ai" / "snapshot.json"
    out.write_text(json.dumps(build(), indent=2), encoding="utf-8")
    print("WROTE:", out)


if __name__ == "__main__":
    main()
