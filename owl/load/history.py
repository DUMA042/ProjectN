"""Employee assignment history helpers.

Shared by nominal-roll ingestion and manual roster edits so both paths close
assignments the same way: the *previous* value is archived with
``end_date = today``, starting from the last open row (or today if none).
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

# Whitelisted so the table name can be interpolated safely.
HISTORY_TABLES: dict[str, str] = {
    "employee_department_history": "department_id",
    "employee_rank_history": "rank_id",
    "employee_gl_history": "gl_id",
    "employee_location_history": "location_id",
}


def history_start(session: Session, table_name: str, id_no: str) -> date:
    """Start date for a history row being closed today.

    Uses the oldest open row's ``start_date`` (the assignment began then), and
    falls back to today when the employee has no open assignment on record.
    """
    if table_name not in HISTORY_TABLES:
        raise ValueError(f"Unknown history table: {table_name}")
    result = session.execute(
        text(
            f"SELECT start_date FROM {table_name} "
            "WHERE id_no = :id_no AND end_date IS NULL "
            "ORDER BY start_date DESC LIMIT 1"
        ),
        {"id_no": id_no},
    ).fetchone()
    if result:
        return result[0]
    return date.today()
