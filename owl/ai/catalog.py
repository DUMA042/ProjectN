"""Unified catalog: entities, fields, relationships, vocabulary.

Single source of truth for what the AI may reference and what the backend
may execute. Field entries carry everything both sides need:

    logical field -> physical table.column, pg_type, human description,
    allowed operators, aggregation/grouping/sorting compatibility,
    visibility (public | sensitive), authorization (open | controlled).

Sensitive fields are retrievable (open policy + audit) but never narrated
verbatim unless user-supplied (see narrate.py). No row data lives here —
only metadata. Reviewed by a human; versioned via snapshot.json.
"""
from __future__ import annotations

VERSION = 1

NUM_OPS = ["=", "!=", "<", "<=", ">", ">=", "IN", "NOT IN", "BETWEEN"]
TEXT_OPS = ["=", "!=", "IN", "NOT IN", "LIKE", "ILIKE"]
NULL_OPS = ["IS NULL", "IS NOT NULL"]
ALL_AGGS = ["COUNT", "COUNT DISTINCT", "SUM", "AVG", "MIN", "MAX"]
NONNUM_AGGS = ["COUNT", "COUNT DISTINCT", "MIN", "MAX"]


def _num(column, desc, **kw):
    spec = {
        "column": column, "pg_type": "numeric",
        "description": desc, "operators": NUM_OPS,
        "aggregatable": ALL_AGGS, "groupable": False, "sortable": True,
        "visibility": "public", "authorization": "open",
    }
    spec.update(kw)
    return spec


def _int(column, desc, **kw):
    spec = _num(column, desc, **kw)
    spec["pg_type"] = "integer"
    return spec


def _text(column, desc, **kw):
    spec = {
        "column": column, "pg_type": "text",
        "description": desc, "operators": TEXT_OPS,
        "aggregatable": NONNUM_AGGS, "groupable": True, "sortable": True,
        "visibility": "public", "authorization": "open",
    }
    spec.update(kw)
    return spec


def _date(column, desc, **kw):
    spec = {
        "column": column, "pg_type": "date",
        "description": desc, "operators": NUM_OPS,
        "aggregatable": NONNUM_AGGS, "groupable": True, "sortable": True,
        "visibility": "public", "authorization": "open",
    }
    spec.update(kw)
    return spec


def _time(column, desc, **kw):
    spec = _date(column, desc, **kw)
    spec["pg_type"] = "time"
    # AVG over time compiles to epoch seconds (see compiler); average
    # check-in/out times are headline HR questions, so this stays allowed.
    spec["aggregatable"] = NONNUM_AGGS + ["AVG"]
    return spec


def _sensitive(column, desc, pg_type="text"):
    return {
        "column": column, "pg_type": pg_type,
        "description": desc, "operators": TEXT_OPS if pg_type == "text" else NUM_OPS,
        "aggregatable": NONNUM_AGGS, "groupable": True, "sortable": True,
        "visibility": "sensitive", "authorization": "controlled",
    }


EMP_ATTRS = {
    "full_name": _sensitive("e.full_name", "Employee full name"),
    "id_no": _sensitive("e.id_no", "Unique employee identifier"),
    "phone_number": _sensitive("e.phone_number", "Employee phone number"),
    "sex": _sensitive("e.sex", "Employee sex"),
    "department": _text("COALESCE(d.department_name, 'Unknown')", "Employee department"),
    "grade_level": _text("COALESCE(gl.gl_name, 'Unknown')", "Grade level"),
    "rank": _text("COALESCE(r.rank_name, 'Unknown')", "Employee rank"),
    "location": _text("COALESCE(l.location_name, 'Unknown')", "Work location"),
    "employment_status": _sensitive("COALESCE(es.status_name, 'Unknown')", "Employment status"),
}

ENTITIES = {
    "employee": {
        "table": "employees",
        "description": "Staff roster, one row per employee.",
        "from": "FROM employees e",
        "fields": dict(EMP_ATTRS),
    },
    "attendance": {
        "table": "attendance_daily",
        "description": "Daily attendance fact, one row per employee per working day.",
        "from": "FROM attendance_daily ad JOIN employees e ON e.id_no = ad.id_no",
        "fields": {
            **EMP_ATTRS,
            "work_date": _date("ad.work_date", "Working day date"),
            "status": _text("ad.status", "Day status: present, absent, leave, training, weekend, holiday, inactive"),
            "checkin_time": _time("ad.checkin_time", "First swipe time"),
            "checkout_time": _time("ad.checkout_time", "Last swipe time"),
            "checkin_status": _text("ad.checkin_status", "Arrival class: Early Arrival, Normal Arrival, Late Arrival"),
            "checkout_status": _text("ad.checkout_status", "Departure class"),
            "minutes_worked": _num("ad.minutes_worked", "Minutes between first and last swipe"),
            "is_working_day": _text("ad.is_working_day", "Whether the day counts as a working day"),
        },
    },
    "leave": {
        "table": "leave_records",
        "description": "Approved leave applications and date spans.",
        "from": "FROM leave_records lr JOIN employees e ON e.id_no = lr.id_no",
        "fields": {
            **EMP_ATTRS,
            "start_date": _date("lr.start_date", "Leave start date"),
            "end_date": _date("COALESCE(lr.end_date, lr.start_date)", "Leave end date (defaults to start)"),
            "leave_type": _text("COALESCE(lt.leave_type_name, 'Unknown')", "Leave category"),
        },
    },
    "training": {
        "table": "employee_trainings",
        "description": "Training assignments and date spans.",
        "from": "FROM employee_trainings tr JOIN employees e ON e.id_no = tr.id_no",
        "fields": {
            **EMP_ATTRS,
            "start_date": _date("tr.start_date", "Training start date"),
            "end_date": _date("tr.end_date", "Training end date"),
            "title": _text("tr.title", "Training title"),
            "venue": _text("COALESCE(v.venue_name, 'Unknown')", "Training venue"),
            "consultant": _text("COALESCE(c.consultant_name, 'Unknown')", "Training consultant"),
        },
    },
    "department": {
        "table": "departments",
        "description": "Departments, aggregatable over staff and attendance.",
        "from": (
            "FROM departments d "
            "LEFT JOIN employees e ON e.department_id = d.department_id "
            "LEFT JOIN attendance_daily ad ON ad.id_no = e.id_no"
        ),
        "fields": {
            "department": _text("COALESCE(d.department_name, 'Unknown')", "Department name"),
            "location": _text("COALESCE(l.location_name, 'Unknown')", "Work location"),
        },
    },
}

# Optional joins by (entity, key); the compiler adds them only when a
# requested field needs them. All are LEFT joins (never change row counts).
JOINS = {
    ("employee", "department"): "LEFT JOIN departments d ON d.department_id = e.department_id",
    ("employee", "grade"): "LEFT JOIN grade_levels gl ON gl.gl_id = e.gl_id",
    ("employee", "rank"): "LEFT JOIN ranks r ON r.rank_id = e.rank_id",
    ("employee", "status"): "LEFT JOIN employee_statuses es ON es.status_id = e.status_id",
    ("employee", "employment_type"): "LEFT JOIN employment_types et ON et.emp_type_id = e.emp_type_id",
    ("employee", "location"): "LEFT JOIN locations l ON e.location_id = l.location_id",
    ("attendance", "department"): "LEFT JOIN departments d ON d.department_id = e.department_id",
    ("attendance", "grade"): "LEFT JOIN grade_levels gl ON gl.gl_id = e.gl_id",
    ("attendance", "rank"): "LEFT JOIN ranks r ON r.rank_id = e.rank_id",
    ("attendance", "status"): "LEFT JOIN employee_statuses es ON es.status_id = e.status_id",
    ("attendance", "employment_type"): "LEFT JOIN employment_types et ON et.emp_type_id = e.emp_type_id",
    ("attendance", "location"): "LEFT JOIN locations l ON e.location_id = l.location_id",
    ("leave", "department"): "LEFT JOIN departments d ON d.department_id = e.department_id",
    ("leave", "grade"): "LEFT JOIN grade_levels gl ON gl.gl_id = e.gl_id",
    ("leave", "rank"): "LEFT JOIN ranks r ON r.rank_id = e.rank_id",
    ("leave", "status"): "LEFT JOIN employee_statuses es ON es.status_id = e.status_id",
    ("leave", "employment_type"): "LEFT JOIN employment_types et ON et.emp_type_id = e.emp_type_id",
    ("leave", "location"): "LEFT JOIN locations l ON e.location_id = l.location_id",
    ("leave", "leave_type"): "LEFT JOIN leave_types lt ON lt.leave_type_id = lr.leave_type_id",
    ("training", "department"): "LEFT JOIN departments d ON d.department_id = e.department_id",
    ("training", "grade"): "LEFT JOIN grade_levels gl ON gl.gl_id = e.gl_id",
    ("training", "rank"): "LEFT JOIN ranks r ON r.rank_id = e.rank_id",
    ("training", "status"): "LEFT JOIN employee_statuses es ON es.status_id = e.status_id",
    ("training", "employment_type"): "LEFT JOIN employment_types et ON et.emp_type_id = e.emp_type_id",
    ("training", "location"): "LEFT JOIN locations l ON e.location_id = l.location_id",
    ("training", "venue"): "LEFT JOIN venues v ON v.venue_id = tr.venue_id",
    ("training", "consultant"): "LEFT JOIN consultants c ON c.consultant_id = tr.consultant_id",
    ("department", "location"): "LEFT JOIN locations l ON e.location_id = l.location_id",
}

# Which join key each field needs beyond the entity base FROM.
FIELD_JOINS = {
    "department": "department",
    "grade_level": "grade",
    "rank": "rank",
    "employment_status": "status",
    "location": "location",
    "leave_type": "leave_type",
    "venue": "venue",
    "consultant": "consultant",
}

# Physical table each join key resolves to (relationship approval + compiler).
JOIN_TABLES = {
    "department": "departments",
    "grade": "grade_levels",
    "rank": "ranks",
    "status": "employee_statuses",
    "employment_type": "employment_types",
    "location": "locations",
    "leave_type": "leave_types",
    "venue": "venues",
    "consultant": "consultants",
}


def join_key_for(source: str, target_table: str) -> str | None:
    """Registry key joining source entity to a physical table, if approved."""
    for (entity, key) in JOINS:
        if entity == source and JOIN_TABLES.get(key) == target_table:
            return key
    return None

# Approved scalar functions and CASE support.
FUNCTIONS = {
    "ROUND": {"args": 2, "types": ["numeric"]},
    "COALESCE": {"args": 2, "types": ["any"]},
    "NULLIF": {"args": 2, "types": ["any"]},
    "EXTRACT_YEAR": {"args": 1, "types": ["date"]},
    "EXTRACT_MONTH": {"args": 1, "types": ["date"]},
    "DATE_TRUNC_MONTH": {"args": 1, "types": ["date"]},
}


# Base tables baked into each entity FROM clause (validator allowlist seed).
ENTITY_BASE_TABLES = {
    "employee": {"employees"},
    "attendance": {"attendance_daily", "employees"},
    "leave": {"leave_records", "employees"},
    "training": {"employee_trainings", "employees"},
    "department": {"departments", "employees", "attendance_daily"},
}

# Physical tables the query engine may touch (validator allowlist).
CATALOG_TABLES = {
    "employees", "attendance_daily", "leave_records", "employee_trainings",
    "departments", "grade_levels", "ranks", "locations", "employee_statuses",
    "employment_types", "leave_types", "venues", "consultants",
}

import re as _re

_SQL_WORDS = {
    "SELECT", "DISTINCT", "FROM", "WHERE", "AND", "OR", "NOT", "IN", "BETWEEN",
    "LIKE", "ILIKE", "IS", "NULL", "GROUP", "BY", "HAVING", "ORDER", "ASC",
    "DESC", "LIMIT", "OFFSET", "AS", "LEFT", "INNER", "JOIN", "ON",
    "CASE", "WHEN", "THEN", "ELSE", "END",
    "COUNT", "SUM", "AVG", "MIN", "MAX",
    "ROUND", "COALESCE", "NULLIF", "EXTRACT", "YEAR", "MONTH",
    "TRUE", "FALSE",
}


def bare_columns() -> set[str]:
    """Bare column identifiers across the registry (validator allowlist).

    Covers field expressions AND join conditions: ON-clause keys such as
    department_id appear only in JOINs, never in selectable fields.
    """
    out = set()
    for ent in ENTITIES.values():
        for spec in ent["fields"].values():
            for tok in _re.findall(r"[A-Za-z_][\w$]*", spec["column"]):
                if tok.upper() not in _SQL_WORDS:
                    out.add(tok)
    for join_sql in JOINS.values():
        for tok in _re.findall(r"[A-Za-z_][\w$]*", join_sql):
            if tok.upper() not in _SQL_WORDS and tok.upper() not in ("LEFT", "JOIN", "ON"):
                out.add(tok)
    return out


# Table aliases the compiler emits per entity + per join key (validator allowlist).
ENTITY_ALIASES = {
    "employee": {"e"},
    "attendance": {"ad", "e"},
    "leave": {"lr", "e"},
    "training": {"tr", "e"},
    "department": {"d", "e", "ad"},
}
JOIN_ALIASES = {
    "department": "d",
    "grade": "gl",
    "rank": "r",
    "status": "es",
    "employment_type": "et",
    "location": "l",
    "leave_type": "lt",
    "venue": "v",
    "consultant": "c",
}

# Human-joinable tables per entity (for prompts; compiler uses JOINS).
ENTITY_JOINS = {
    "employee": ["departments", "grade_levels", "ranks", "employee_statuses", "employment_types", "locations"],
    "attendance": ["employees", "departments", "grade_levels", "ranks", "employee_statuses", "employment_types", "locations"],
    "leave": ["employees", "leave_types", "departments", "grade_levels", "ranks", "employee_statuses", "employment_types", "locations"],
    "training": ["employees", "venues", "consultants", "departments", "grade_levels", "ranks", "employee_statuses", "employment_types", "locations"],
    "department": ["employees", "attendance_daily", "locations"],
}


def for_model() -> dict:
    """Sanitized catalog for prompts: structure + vocabulary, never row data."""
    out = {"version": VERSION, "entities": {}}
    for name, ent in ENTITIES.items():
        out["entities"][name] = {
            "description": ent["description"],
            "fields": {
                fname: {
                    "description": f["description"],
                    "type": f["pg_type"],
                    "operators": f["operators"],
                    "aggregatable": f["aggregatable"],
                    "visibility": f["visibility"],
                }
                for fname, f in ent["fields"].items()
            },
            "joins": ENTITY_JOINS.get(name, []),
        }
    return out
