"""Builds the `attendance_daily` analytics fact table from the rule-driven
classification. One row per employee per calendar day, so every downstream
attendance question is a fast GROUP BY joined to employee dimensions.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta

from psycopg2.extras import execute_values
from sqlalchemy import text

from owl.load.database import get_session
from owl.logger import get_logger
from owl.analytics.classification import (
    DAY_NAMES,
    classify_checkin,
    classify_checkout,
    classify_day,
    hm_to_min,
    load_rule_context,
)

log = get_logger(__name__)

_INSERT_COLS = (
    "id_no, work_date, status, checkin_time, checkout_time, "
    "checkin_status, checkout_status, minutes_worked, is_working_day"
)


def _flush(cur, batch):
    if batch:
        execute_values(
            cur,
            f"INSERT INTO attendance_daily ({_INSERT_COLS}) VALUES %s",
            batch,
            page_size=10000,
        )


def _data_span(session):
    """Span for the attendance fact table — based on the swipe data only.

    Leave/training tables are used by their own analytics and may contain
    erroneous or far-future dates (e.g. a leave year of 0202), so they must not
    widen the attendance window.
    """
    row = session.execute(text(
        "SELECT MIN(swipe_time::date), MAX(swipe_time::date) FROM employee_card_swipes"
    )).fetchone()
    return (row[0], row[1]) if row else (None, None)


def rebuild_attendance_daily(start: date | None = None, end: date | None = None) -> dict:
    """Rebuild the attendance_daily fact table. Returns row-count metadata."""
    ctx = load_rule_context()
    working_hours = ctx["working_hours"]
    incomplete_hours = ctx["incomplete_hours"]

    with get_session() as s:
        if start is None or end is None:
            span_min, span_max = _data_span(s)
            start = start or span_min
            end = end or span_max
        if not start or not end:
            return {"rows": 0, "start": None, "end": None}

        # Employee eligibility (rule-driven)
        emp_rows = s.execute(text("""
            SELECT e.id_no, COALESCE(es.status_name, '') AS status_name
            FROM employees e
            LEFT JOIN employee_statuses es ON e.status_id = es.status_id
        """)).fetchall()
        is_active_map = {r[0]: (r[1].strip().lower() in ctx["active_statuses"]) for r in emp_rows}

        # Daily swipe edges
        swipe_rows = s.execute(text("""
            SELECT id_no, swipe_time::date AS d, MIN(swipe_time) AS cin, MAX(swipe_time) AS cout
            FROM employee_card_swipes
            WHERE swipe_time::date BETWEEN :sd AND :ed
            GROUP BY id_no, swipe_time::date
        """), {"sd": start, "ed": end}).fetchall()
        swipe_map = {}          # (id_no, date) -> (cin_time_str, cout_time_str)
        swipe_dates = defaultdict(set)
        for r in swipe_rows:
            cin = r[2].strftime("%H:%M") if r[2] else None
            cout = r[3].strftime("%H:%M") if r[3] else None
            swipe_map[(r[0], r[1])] = (cin, cout)
            swipe_dates[r[0]].add(r[1])

        leave_rows = s.execute(text("""
            SELECT id_no, start_date, COALESCE(end_date, start_date) AS end_date
            FROM leave_records
            WHERE start_date <= :ed AND COALESCE(end_date, start_date) >= :sd
        """), {"sd": start, "ed": end}).fetchall()
        leave_ranges = defaultdict(list)
        for r in leave_rows:
            leave_ranges[r[0]].append((r[1], r[2]))

        train_rows = s.execute(text("""
            SELECT id_no, start_date, end_date
            FROM employee_trainings
            WHERE start_date <= :ed AND end_date >= :sd
        """), {"sd": start, "ed": end}).fetchall()
        train_ranges = defaultdict(list)
        for r in train_rows:
            train_ranges[r[0]].append((r[1], r[2]))

        s.execute(text("TRUNCATE attendance_daily"))
        raw = s.connection().connection
        dbcur = raw.cursor()
        today = date.today()
        batch = []
        total = 0
        for eid, is_active in is_active_map.items():
            emp_leave = leave_ranges.get(eid, [])
            emp_train = train_ranges.get(eid, [])
            emp_swipes = swipe_dates.get(eid, set())
            cur = start
            while cur <= end:
                status = classify_day(cur, emp_leave, emp_train, emp_swipes, ctx, is_active, today)
                is_working = (cur.weekday() + 1) in ctx["working_dows"] and cur not in ctx["holiday_set"]
                cin, cout = swipe_map.get((eid, cur), (None, None))
                wh = working_hours.get(DAY_NAMES[cur.weekday()])
                cin_status = classify_checkin(cin, wh)
                cout_status = classify_checkout(cin, cout, wh, incomplete_hours)
                minutes = None
                if cin and cout:
                    cim, com = hm_to_min(cin), hm_to_min(cout)
                    if cim is not None and com is not None and com >= cim:
                        minutes = com - cim
                batch.append((eid, cur, status, cin, cout, cin_status, cout_status, minutes, is_working))
                if len(batch) >= 10000:
                    _flush(dbcur, batch)
                    total += len(batch)
                    batch = []
                cur += timedelta(days=1)
        _flush(dbcur, batch)
        total += len(batch)
        dbcur.close()

        s.commit()

    log.info(f"attendance_daily rebuilt: {total} rows ({start}..{end})")
    return {"rows": total, "start": start.isoformat(), "end": end.isoformat()}


def clear_attendance_daily() -> None:
    with get_session() as s:
        s.execute(text("TRUNCATE attendance_daily"))
        s.commit()
