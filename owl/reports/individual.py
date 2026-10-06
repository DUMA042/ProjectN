"""Individual attendance report data: roster -> day cells -> summaries.

Fully deterministic (no AI, no hashing): day status comes from the shared
rule-driven classifier, grid codes from swipe times + the incomplete rule,
and summaries from exact counts. Processed data never leaves this system,
so real names render directly.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from owl.analytics.classification import (
    DAY_NAMES,
    classify_checkin,
    classify_checkout,
    classify_day,
    hm_to_min,
)

MAX_IDS_PER_BUILD = 2000
MAX_RANGE_DAYS = 93


def report_dates(
    sd: date, ed: date, working_dows: set[int], holidays: set[date]
) -> list[date]:
    """Grid columns: rule-configured working days plus holidays (sorted).

    Non-working, non-holiday days (e.g. Sundays) get no column at all —
    they are absent, not blank. Mirrors the reference "all workdays
    present + holiday" formula.
    """
    out = []
    current = sd
    while current <= ed:
        if current.isoweekday() in working_dows or current in holidays:
            out.append(current)
        current += timedelta(days=1)
    return out


def period_label(sd: date, ed: date) -> str:
    if sd.year == ed.year and sd.month == ed.month:
        return sd.strftime("%B %Y")
    fmt = lambda d: f"{d.day} {d.strftime('%b')} {d.year}"
    return f"{fmt(sd)} to {fmt(ed)}"


def file_stem(location: str, sd: date, ed: date) -> str:
    loc = re.sub(r"[^\w]+", "-", (location or "All").strip()).strip("-") or "All"
    per = period_label(sd, ed).replace(" ", "_")
    return f"Individual_Attendance_Details_{per}_{loc}"[:120]


def _parse_hhmm(value: object) -> int | None:
    try:
        h, m = str(value).strip().split(":")[:2]
        return int(h) * 60 + int(m)
    except (ValueError, IndexError):
        return None


def resolve_roster(
    session: Session,
    location: str = "",
    departments: list[str] | None = None,
    employee_ids: list[str] | None = None,
    search: str = "",
) -> list[dict[str, Any]]:
    """Employees matching the selection (ordered by department, name).

    Explicit IDs bypass scope filters entirely. Otherwise location,
    departments, and the name/ID search all narrow the roster — so "All"
    plus a search builds exactly the matching set.
    """
    where = ["TRUE"]
    params: dict[str, Any] = {}
    employee_ids = [str(v) for v in (employee_ids or []) if str(v).strip()]
    if len(employee_ids) > MAX_IDS_PER_BUILD:
        raise ValueError(f"Too many individuals (max {MAX_IDS_PER_BUILD})")
    if employee_ids:
        # Explicit picks bypass every scope filter.
        where.append("e.id_no IN (" + ", ".join(
            f":eid{i}" for i in range(len(employee_ids))) + ")")
        for i, v in enumerate(employee_ids):
            params[f"eid{i}"] = v
    else:
        if location and location.lower() not in ("all", "all locations", "all location"):
            where.append("LOWER(l.location_name) = LOWER(:loc)")
            params["loc"] = location
        departments = [d for d in (departments or []) if d]
        if departments:
            where.append("LOWER(d.department_name) IN (" + ", ".join(
                f":dept{i}" for i in range(len(departments))) + ")")
            for i, d in enumerate(departments):
                params[f"dept{i}"] = d.lower()
        search = (search or "").strip().lower()
        if search:
            where.append("(LOWER(e.full_name) LIKE :q OR LOWER(e.id_no) LIKE :q)")
            params["q"] = f"%{search}%"
    rows = session.execute(text(f"""
        SELECT e.id_no, e.full_name, e.sex,
               COALESCE(d.department_name, 'Unknown'),
               COALESCE(gl.gl_name, 'Unknown'),
               COALESCE(r.rank_name, 'Unknown'),
               COALESCE(es.status_name, 'Unknown'),
               COALESCE(l.location_name, 'Unknown')
        FROM employees e
        LEFT JOIN departments d ON e.department_id = d.department_id
        LEFT JOIN grade_levels gl ON e.gl_id = gl.gl_id
        LEFT JOIN ranks r ON e.rank_id = r.rank_id
        LEFT JOIN employee_statuses es ON e.status_id = es.status_id
        LEFT JOIN locations l ON e.location_id = l.location_id
        WHERE {" AND ".join(where)}
        ORDER BY d.department_name NULLS LAST, e.full_name
    """), params).fetchall()
    return [
        {"id_no": r[0], "full_name": r[1], "sex": r[2], "department": r[3],
         "grade_level": r[4], "rank": r[5], "employment_status": r[6],
         "location": r[7]}
        for r in rows
    ]


def _chunked(values: list, size: int = 500):
    for i in range(0, len(values), size):
        yield values[i:i + size]


def load_day_data(
    session: Session, id_nos: list[str], sd: date, ed: date
) -> dict[str, dict[str, Any]]:
    """Batched swipes + leave/training ranges per employee (no N+1)."""
    data: dict[str, dict[str, Any]] = {
        i: {"swipes": {}, "leaves": [], "trainings": []} for i in id_nos
    }
    for chunk in _chunked(id_nos):
        ph = ", ".join(f":c{j}" for j in range(len(chunk)))
        cp = {f"c{j}": v for j, v in enumerate(chunk)}
        for r in session.execute(text(f"""
            SELECT id_no, DATE(swipe_time), MIN(swipe_time), MAX(swipe_time)
            FROM employee_card_swipes
            WHERE id_no IN ({ph}) AND swipe_time::date BETWEEN :sd AND :ed
            GROUP BY id_no, DATE(swipe_time)
        """), {**cp, "sd": sd, "ed": ed}).fetchall():
            data[str(r[0])]["swipes"][r[1]] = (r[2], r[3])
        for r in session.execute(text(f"""
            SELECT id_no, start_date, COALESCE(end_date, start_date)
            FROM leave_records
            WHERE id_no IN ({ph}) AND start_date <= :ed
              AND COALESCE(end_date, start_date) >= :sd
        """), {**cp, "sd": sd, "ed": ed}).fetchall():
            data[str(r[0])]["leaves"].append((r[1], r[2]))
        for r in session.execute(text(f"""
            SELECT id_no, start_date, end_date
            FROM employee_trainings
            WHERE id_no IN ({ph}) AND start_date <= :ed AND end_date >= :sd
        """), {**cp, "sd": sd, "ed": ed}).fetchall():
            data[str(r[0])]["trainings"].append((r[1], r[2]))
    return data


def _late_after_minutes(working_hours: dict, wd: int) -> int | None:
    try:
        return _parse_hhmm((working_hours.get(DAY_NAMES[wd]) or {}).get("checkin", {}).get("late_after"))
    except (AttributeError, TypeError):
        return None


class ReportContext:
    """Rule-derived context shared across employees (loaded once per build)."""

    def __init__(self, working_hours, holidays, active_statuses,
                 incomplete_hours, working_dows, leave_overrides_training, today):
        self.working_hours = working_hours or {}
        self.holiday_set = holidays
        self.active_statuses = {s.lower() for s in (active_statuses or [])}
        self.incomplete_minutes = float(incomplete_hours or 1) * 60.0
        self.working_dows = set(working_dows or [])
        self.leave_overrides_training = bool(leave_overrides_training)
        self.today = today

    def is_active(self, employment_status: str) -> bool:
        return str(employment_status or "").strip().lower() in self.active_statuses

    def is_working_day(self, d: date) -> bool:
        # ISO weekdays (1=Mon), matching get_working_weekdays() + the
        # shared classifier's (weekday() + 1) convention.
        return d.isoweekday() in self.working_dows and d not in self.holiday_set


def load_context() -> ReportContext:
    from datetime import date as _date

    from owl.rules.engine import get_rule
    from owl.rules.query_builder import get_active_statuses, get_working_weekdays

    holidays: set[date] = set()
    for raw in (get_rule("holidays", {}) or {}).get("dates", []) or []:
        try:
            holidays.add(date.fromisoformat(str(raw)))
        except ValueError:
            pass
    return ReportContext(
        working_hours=get_rule("working_hours", {}) or {},
        holidays=holidays,
        active_statuses=get_active_statuses(),
        incomplete_hours=(get_rule("incomplete_threshold", {"hours": 1}) or {}).get("hours", 1),
        working_dows=get_working_weekdays(),
        leave_overrides_training=get_rule("leave_overrides_training", True),
        today=_date.today(),
    )


def build_employee_report(
    emp: dict[str, Any],
    day_data: dict[str, Any],
    dates: list[date],
    ctx: ReportContext,
) -> dict[str, Any]:
    """Day cells + 16-field summary for one employee (pure)."""
    swipes = day_data.get("swipes", {})
    leaves = day_data.get("leaves", [])
    trainings = day_data.get("trainings", [])
    active = ctx.is_active(emp.get("employment_status", ""))
    ctx_day = {
        "working_dows": ctx.working_dows,
        "holiday_set": ctx.holiday_set,
        "leave_overrides_training": ctx.leave_overrides_training,
    }
    swipe_dates = {d for d in swipes if isinstance(d, date)}
    days = []
    counts = {"present": 0, "absent": 0, "leave": 0, "training": 0}
    expected = 0
    late_days = late_minutes = early_deps = incomplete_days = 0
    work_minutes: list[int] = []
    for d in dates:
        if d in ctx.holiday_set:
            days.append({"date": d, "code": "H", "ci": "H", "co": "H"})
            continue
        status = classify_day(d, leaves, trainings, swipe_dates, ctx_day, active, ctx.today)
        if status in counts:
            counts[status] += 1
        if ctx.is_working_day(d):
            expected += 1
        ci = co = code = ""
        row = swipes.get(d)
        ci_t = row[0].strftime("%H:%M") if row and row[0] else None
        co_t = row[1].strftime("%H:%M") if row and row[1] else None
        if status == "leave":
            code, ci, co = "L", "L", "L"
        elif status == "training":
            code, ci, co = "T", "T", "T"
        elif status == "present":
            ci = ci_t or ""
            gap = None
            if ci_t and co_t:
                a, b = hm_to_min(ci_t), hm_to_min(co_t)
                gap = b - a if a is not None and b is not None and b >= a else None
            if co_t is None or (gap is not None and gap < ctx.incomplete_minutes):
                co = "IN"
                incomplete_days += 1
            else:
                co = co_t or ""
            wh = ctx.working_hours.get(DAY_NAMES[d.weekday()])
            if classify_checkin(ci_t, wh) == "Late Arrival":
                late_days += 1
                cutoff = _late_after_minutes(ctx.working_hours, d.weekday())
                cim = hm_to_min(ci_t) if ci_t else None
                if cutoff is not None and cim is not None and cim > cutoff:
                    late_minutes += cim - cutoff
            if classify_checkout(ci_t, co_t, wh, ctx.incomplete_minutes / 60.0) == "Early Departure":
                early_deps += 1
            if ci_t and co_t and gap is not None:
                work_minutes.append(gap)
        days.append({"date": d, "code": code, "ci": ci, "co": co})
    total_work = sum(work_minutes)
    rate = round(100.0 * counts["present"] / expected, 1) if expected else 0.0
    return {
        "employee": emp,
        "days": days,
        "summary": {
            "expected_workdays": expected,
            "days_present": counts["present"],
            "days_absent": counts["absent"],
            "days_on_leave": counts["leave"],
            "days_in_training": counts["training"],
            "attendance_rate_pct": rate,
            "days_late": late_days,
            "total_minutes_late": late_minutes,
            "early_departures": early_deps,
            "incomplete_swipe_days": incomplete_days,
            "total_hours_worked": round(total_work / 60.0, 2),
            "avg_daily_hours_worked": round(total_work / 60.0 / counts["present"], 2) if counts["present"] else None,
        },
    }
