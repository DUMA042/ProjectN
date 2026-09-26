"""Today snapshot + data freshness for the Pulse tab.

Everything is rule-driven: working day / late classification come from
rules_settings just like the fact-table builder. All queries honour the page
scope (location + dimension filters) through the whitelisted scope builder.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import text

from owl.analytics.classification import DAY_NAMES, classify_checkin, load_rule_context
from owl.analytics.filters import build_scope
from owl.load.database import get_session


def today_snapshot(filters: dict | None = None) -> dict:
    ctx = load_rule_context()
    today = date.today()
    is_working_day = (today.weekday() + 1) in ctx["working_dows"] and today not in ctx["holiday_set"]
    wh = (ctx["working_hours"] or {}).get(DAY_NAMES[today.weekday()])

    with get_session() as s:
        params: dict = {"today": today}
        joins, where = build_scope(filters, params)

        active_statuses = sorted(ctx["active_statuses"])
        status_list = ", ".join(f"'{s_}'" for s_ in active_statuses)

        active_count = s.execute(text(f"""
            SELECT COUNT(*) FROM employees e {joins}
            {where + " AND" if where else "WHERE"} LOWER(COALESCE((SELECT status_name FROM employee_statuses es WHERE es.status_id = e.status_id), '')) IN ({status_list})
        """), params).scalar() or 0

        # Today's first/last swipe per employee (scoped)
        swipe_rows = s.execute(text(f"""
            SELECT cs.id_no,
                   MIN(cs.swipe_time) AS first_swipe,
                   MAX(cs.swipe_time) AS last_swipe,
                   COUNT(*) AS n
            FROM employee_card_swipes cs
            JOIN employees e ON e.id_no = cs.id_no
            {joins}
            {where + " AND" if where else "WHERE"} cs.swipe_time::date = :today
            GROUP BY cs.id_no
        """), params).fetchall()

        swipers = len(swipe_rows)
        total_swipes = sum(r[3] for r in swipe_rows)
        late_count = 0
        last_swipe = None
        for r in swipe_rows:
            first_hm = r[1].strftime("%H:%M") if r[1] else None
            if classify_checkin(first_hm, wh) == "Late Arrival":
                late_count += 1
            if r[2] and (last_swipe is None or r[2] > last_swipe):
                last_swipe = r[2]

        leave_today = s.execute(text(f"""
            SELECT COUNT(DISTINCT lr.id_no) FROM leave_records lr
            JOIN employees e ON e.id_no = lr.id_no
            {joins}
            {where + " AND" if where else "WHERE"} lr.start_date <= :today
              AND COALESCE(lr.end_date, lr.start_date) >= :today
        """), params).scalar() or 0

        training_today = s.execute(text(f"""
            SELECT COUNT(DISTINCT tr.id_no) FROM employee_trainings tr
            JOIN employees e ON e.id_no = tr.id_no
            {joins}
            {where + " AND" if where else "WHERE"} tr.start_date <= :today
              AND tr.end_date >= :today
        """), params).scalar() or 0

    no_swipe = (active_count - swipers) if (is_working_day and active_count >= swipers) else None

    return {
        "date": today.isoformat(),
        "is_working_day": is_working_day,
        "active_employees": active_count,
        "total_swipes": total_swipes,
        "swipers": swipers,
        "late_so_far": late_count,
        "on_leave": leave_today,
        "in_training": training_today,
        "no_swipe_yet": no_swipe,
        "last_swipe": last_swipe.isoformat() if last_swipe else None,
    }


def freshness_snapshot(filters: dict | None = None) -> dict:
    """Data-health signals: fact-table span, last ingest, quarantine backlog."""
    with get_session() as s:
        params: dict = {}
        joins, where = build_scope(filters, params)

        fact_span = s.execute(text("SELECT MIN(work_date), MAX(work_date), COUNT(*) FROM attendance_daily")).fetchone()

        last_ingest = s.execute(text("""
            SELECT original_filename, report_type, status, created_at, processed_at
            FROM file_ingestion_meta ORDER BY created_at DESC LIMIT 1
        """)).fetchone()

        quarantine_rows = 0
        for table in ("quarantine_card_swipes", "quarantine_trainings"):
            try:
                quarantine_rows += s.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0
            except Exception:  # noqa: BLE001 — table may not exist yet
                pass

        coverage = None
        if fact_span and fact_span[2]:
            row = s.execute(text(f"""
                SELECT
                  COUNT(DISTINCT e.id_no) AS all_emp,
                  COUNT(DISTINCT e.id_no) FILTER (WHERE ad.status = 'present') AS with_swipe
                FROM attendance_daily ad JOIN employees e ON e.id_no = ad.id_no
                {joins} {where}
            """), params).fetchone()
            if row and row[0]:
                coverage = round(100.0 * row[1] / row[0], 1)

    return {
        "fact_start": fact_span[0].isoformat() if fact_span and fact_span[0] else None,
        "fact_end": fact_span[1].isoformat() if fact_span and fact_span[1] else None,
        "fact_rows": fact_span[2] if fact_span else 0,
        "fact_is_empty": not fact_span or not fact_span[2],
        "coverage": coverage,
        "last_ingest": {
            "filename": last_ingest[0],
            "report_type": last_ingest[1],
            "status": last_ingest[2],
            "created_at": last_ingest[3].isoformat() if last_ingest and last_ingest[3] else None,
            "processed_at": last_ingest[4].isoformat() if last_ingest and last_ingest[4] else None,
        } if last_ingest else None,
        "quarantine_rows": quarantine_rows,
    }
