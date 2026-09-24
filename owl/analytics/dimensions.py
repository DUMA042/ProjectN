"""Whitelisted analytical dimensions (employee attributes + time buckets).

Each dimension maps a stable key to a SQL expression and the JOIN(s) required to
resolve it. The engine only ever uses keys from these registries, so user input
can never inject SQL.
"""
from __future__ import annotations

# `expr` may reference aliases: e (employees), d (departments), gl (grade_levels),
# r (ranks), et (employment_types), es (employee_statuses), l (locations).
DIMENSIONS: dict[str, dict] = {
    "location": {
        "label": "Location",
        "expr": "COALESCE(l.location_name, 'Unknown')",
        "join": "LEFT JOIN locations l ON e.location_id = l.location_id",
    },
    "department": {
        "label": "Department",
        "expr": "COALESCE(d.department_name, 'Unknown')",
        "join": "LEFT JOIN departments d ON e.department_id = d.department_id",
    },
    "grade_level": {
        "label": "Grade Level",
        "expr": "COALESCE(gl.gl_name, 'Unknown')",
        "join": "LEFT JOIN grade_levels gl ON e.gl_id = gl.gl_id",
    },
    "rank": {
        "label": "Rank",
        "expr": "COALESCE(r.rank_name, 'Unknown')",
        "join": "LEFT JOIN ranks r ON e.rank_id = r.rank_id",
    },
    "employment_type": {
        "label": "Employment Type",
        "expr": "COALESCE(et.emp_type_name, 'Unknown')",
        "join": "LEFT JOIN employment_types et ON e.emp_type_id = et.emp_type_id",
    },
    "status": {
        "label": "Status",
        "expr": "COALESCE(es.status_name, 'Unknown')",
        "join": "LEFT JOIN employee_statuses es ON e.status_id = es.status_id",
    },
    "sex": {
        "label": "Sex",
        "expr": "COALESCE(e.sex, 'Unknown')",
        "join": "",
    },
    "zone": {
        "label": "Geographical Zone",
        "expr": "COALESCE(e.geographical_zone, 'Unknown')",
        "join": "",
    },
    "employee": {
        "label": "Employee",
        "expr": "e.full_name",
        "join": "",
    },
    "employee_id": {
        "label": "Employee ID",
        "expr": "e.id_no",
        "join": "",
    },
}

# Time buckets reference the domain's date column via the placeholder {date_col}.
TIME_DIMENSIONS: dict[str, dict] = {
    "day": {"label": "Day", "expr": "{date_col}"},
    "week": {"label": "Week", "expr": "date_trunc('week', {date_col})::date"},
    "month": {"label": "Month", "expr": "date_trunc('month', {date_col})::date"},
    "quarter": {"label": "Quarter", "expr": "date_trunc('quarter', {date_col})::date"},
}

ALL_DIMENSION_KEYS = list(DIMENSIONS.keys()) + list(TIME_DIMENSIONS.keys())


def dimension_expr(key: str, date_col: str) -> str | None:
    if key in DIMENSIONS:
        return DIMENSIONS[key]["expr"]
    if key in TIME_DIMENSIONS:
        return TIME_DIMENSIONS[key]["expr"].format(date_col=date_col)
    return None


def dimension_label(key: str) -> str:
    return DIMENSIONS.get(key, TIME_DIMENSIONS.get(key, {})).get("label", key)


def dimensions_metadata() -> list[dict]:
    out = []
    for key, meta in DIMENSIONS.items():
        out.append({"key": key, "label": meta["label"], "kind": "attribute"})
    for key, meta in TIME_DIMENSIONS.items():
        out.append({"key": key, "label": meta["label"], "kind": "time"})
    return out
