"""Whitelisted metrics per analytics domain.

Metrics are SQL aggregate expressions. Rates/coverage are computed from the
rule-driven fact table (`attendance_daily`), so working days, holidays, eligible
statuses, etc. are all honoured.
"""
from __future__ import annotations

ATTENDANCE_METRICS: dict[str, dict] = {
    "working_days": {"label": "Working Days", "expr": "COUNT(*) FILTER (WHERE ad.is_working_day)", "type": "int"},
    "present_days": {"label": "Present Days", "expr": "COUNT(*) FILTER (WHERE ad.status = 'present')", "type": "int"},
    "absent_days": {"label": "Absent Days", "expr": "COUNT(*) FILTER (WHERE ad.status = 'absent')", "type": "int"},
    "leave_days": {"label": "Leave Days", "expr": "COUNT(*) FILTER (WHERE ad.status = 'leave')", "type": "int"},
    "training_days": {"label": "Training Days", "expr": "COUNT(*) FILTER (WHERE ad.status = 'training')", "type": "int"},
    "late_arrivals": {"label": "Late Arrivals", "expr": "COUNT(*) FILTER (WHERE ad.checkin_status = 'Late Arrival')", "type": "int"},
    "early_departures": {"label": "Early Departures", "expr": "COUNT(*) FILTER (WHERE ad.checkout_status = 'Early Departure')", "type": "int"},
    "incomplete_days": {"label": "Incomplete Days", "expr": "COUNT(*) FILTER (WHERE ad.checkout_status = 'Incomplete')", "type": "int"},
    "attendance_rate": {
        "label": "Attendance Rate",
        "expr": "ROUND(100.0 * COUNT(*) FILTER (WHERE ad.status = 'present') / NULLIF(COUNT(*) FILTER (WHERE ad.is_working_day), 0), 1)",
        "type": "pct",
    },
    "absence_rate": {
        "label": "Absence Rate",
        "expr": "ROUND(100.0 * COUNT(*) FILTER (WHERE ad.status = 'absent') / NULLIF(COUNT(*) FILTER (WHERE ad.is_working_day), 0), 1)",
        "type": "pct",
    },
    "avg_work_minutes": {"label": "Avg Work Minutes", "expr": "ROUND(AVG(ad.minutes_worked))", "type": "int"},
    "coverage": {
        "label": "Coverage",
        "expr": "ROUND(100.0 * COUNT(DISTINCT e.id_no) FILTER (WHERE ad.status = 'present') / NULLIF(COUNT(DISTINCT e.id_no), 0), 1)",
        "type": "pct",
    },
}

LEAVE_METRICS: dict[str, dict] = {
    "leave_records": {"label": "Leave Records", "expr": "COUNT(*)", "type": "int"},
    "unique_staff": {"label": "Staff on Leave", "expr": "COUNT(DISTINCT lr.id_no)", "type": "int"},
    "leave_types_used": {"label": "Leave Types", "expr": "COUNT(DISTINCT lr.leave_type_id)", "type": "int"},
    "avg_duration_days": {
        "label": "Avg Duration (days)",
        # Guard against clearly-invalid spans (e.g. a leave year of 0202).
        "expr": (
            "ROUND(AVG((COALESCE(lr.end_date, lr.start_date) - lr.start_date) + 1) "
            "FILTER (WHERE (COALESCE(lr.end_date, lr.start_date) - lr.start_date) BETWEEN 0 AND 366), 1)"
        ),
        "type": "num",
    },
}

TRAINING_METRICS: dict[str, dict] = {
    "activities": {"label": "Training Activities", "expr": "COUNT(*)", "type": "int"},
    "participants": {"label": "Participants", "expr": "COUNT(DISTINCT tr.id_no)", "type": "int"},
    "venues": {"label": "Venues", "expr": "COUNT(DISTINCT tr.venue_id)", "type": "int"},
    "consultants": {"label": "Consultants", "expr": "COUNT(DISTINCT tr.consultant_id)", "type": "int"},
    "avg_duration_days": {
        "label": "Avg Duration (days)",
        "expr": "ROUND(AVG((tr.end_date - tr.start_date) + 1), 1)",
        "type": "num",
    },
}

EMPLOYEE_METRICS: dict[str, dict] = {
    "employees": {"label": "Employees", "expr": "COUNT(DISTINCT e.id_no)", "type": "int"},
    "active": {
        "label": "Active",
        "expr": "COUNT(DISTINCT e.id_no) FILTER (WHERE LOWER(COALESCE(es.status_name, '')) IN ({active_statuses}))",
        "type": "int",
    },
}

DOMAIN_METRICS = {
    "attendance": ATTENDANCE_METRICS,
    "leave": LEAVE_METRICS,
    "training": TRAINING_METRICS,
    "employees": EMPLOYEE_METRICS,
}
