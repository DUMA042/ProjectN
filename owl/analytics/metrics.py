"""Unified metric catalog for the Management workspace.

Every metric declares its subject (attendance/leave/training/employees), type
and polarity so the UI can group pickers and color deltas without hardcoding.
Metric expressions remain whitelisted SQL aggregates — user input never enters
SQL, only metric keys from this registry.
"""
from __future__ import annotations

ATTENDANCE_METRICS: dict[str, dict] = {
    "working_days": {"label": "Working Days", "expr": "COUNT(*) FILTER (WHERE ad.is_working_day)", "type": "int"},
    "present_days": {"label": "Present Days", "expr": "COUNT(*) FILTER (WHERE ad.status = 'present')", "type": "int", "polarity": "up_good"},
    "absent_days": {"label": "Absent Days", "expr": "COUNT(*) FILTER (WHERE ad.status = 'absent')", "type": "int", "polarity": "up_bad"},
    "leave_days": {"label": "Leave Days", "expr": "COUNT(*) FILTER (WHERE ad.status = 'leave')", "type": "int", "polarity": "up_bad"},
    "training_days": {"label": "Training Days", "expr": "COUNT(*) FILTER (WHERE ad.status = 'training')", "type": "int"},
    "late_arrivals": {"label": "Late Arrivals", "expr": "COUNT(*) FILTER (WHERE ad.checkin_status = 'Late Arrival')", "type": "int", "polarity": "up_bad"},
    "early_arrivals": {"label": "Early Arrivals", "expr": "COUNT(*) FILTER (WHERE ad.checkin_status = 'Early Arrival')", "type": "int", "polarity": "up_good"},
    "normal_arrivals": {"label": "Normal Arrivals", "expr": "COUNT(*) FILTER (WHERE ad.checkin_status = 'Normal Arrival')", "type": "int"},
    "early_departures": {"label": "Early Departures", "expr": "COUNT(*) FILTER (WHERE ad.checkout_status = 'Early Departure')", "type": "int", "polarity": "up_bad"},
    "incomplete_days": {"label": "Incomplete Days", "expr": "COUNT(*) FILTER (WHERE ad.checkout_status = 'Incomplete')", "type": "int", "polarity": "up_bad"},
    "attendance_rate": {
        "label": "Attendance Rate",
        "expr": "ROUND(100.0 * COUNT(*) FILTER (WHERE ad.status = 'present') / NULLIF(COUNT(*) FILTER (WHERE ad.is_working_day), 0), 1)",
        "type": "pct",
        "polarity": "up_good",
        # Blue above / red below this pivot (user-facing good/bad line).
        "pivot": 60,
    },
    "absence_rate": {
        "label": "Absence Rate",
        "expr": "ROUND(100.0 * COUNT(*) FILTER (WHERE ad.status = 'absent') / NULLIF(COUNT(*) FILTER (WHERE ad.is_working_day), 0), 1)",
        "type": "pct",
        "polarity": "up_bad",
        # User rule: absent beyond 30% of working days reads red.
        "pivot": 30,
    },
    "avg_work_minutes": {"label": "Avg Work Minutes", "expr": "ROUND(AVG(ad.minutes_worked))", "type": "int"},
    "coverage": {
        "label": "Coverage",
        "expr": "ROUND(100.0 * COUNT(DISTINCT e.id_no) FILTER (WHERE ad.status = 'present') / NULLIF(COUNT(DISTINCT e.id_no), 0), 1)",
        "type": "pct",
        "polarity": "up_good",
        "pivot": 60,
    },
}

LEAVE_METRICS: dict[str, dict] = {
    "leave_records": {"label": "Leave Records", "expr": "COUNT(*)", "type": "int", "polarity": "up_bad"},
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
    "employees": {"label": "Headcount", "expr": "COUNT(DISTINCT e.id_no)", "type": "int"},
    "active": {
        "label": "Active",
        "expr": "COUNT(DISTINCT e.id_no) FILTER (WHERE LOWER(COALESCE(es.status_name, '')) IN ({active_statuses}))",
        "type": "int",
        "polarity": "up_good",
    },
}

DOMAIN_METRICS = {
    "attendance": ATTENDANCE_METRICS,
    "leave": LEAVE_METRICS,
    "training": TRAINING_METRICS,
    "employees": EMPLOYEE_METRICS,
}

# Display labels for the "subject" grouping shown in metric pickers.
METRIC_DOMAINS: dict[str, str] = {
    "attendance": "Attendance",
    "leave": "Leave",
    "training": "Training",
    "employees": "Workforce",
}


def metrics_catalog() -> list[dict]:
    """Flat catalog of every metric with its subject, type, polarity and pivot."""
    out: list[dict] = []
    for domain, metrics in DOMAIN_METRICS.items():
        for key, meta in metrics.items():
            out.append({
                "key": key,
                "domain": domain,
                "label": meta["label"],
                "type": meta.get("type", "int"),
                "polarity": meta.get("polarity"),
                "pivot": meta.get("pivot"),
            })
    return out
