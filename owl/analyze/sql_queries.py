"""
owl.analyze.sql_queries
~~~~~~~~~~~~~~~~~~~~~~~~
Repository of reusable, named SQL aggregations.

Design
------
* All queries use SQLAlchemy ``text()`` for raw SQL — lets us write idiomatic,
  readable PostgreSQL without fighting the ORM query builder for complex
  analytical expressions.
* Each function accepts a ``Session`` (or ``Connection``) and returns a
  pandas DataFrame, making results immediately usable for further analysis.
* Query strings are defined as module-level constants for easy linting and
  future migration to a ``*.sql`` file loader if queries grow large.

Adding queries
--------------
1. Define the SQL string as a module constant (``_SQL_<NAME>``).
2. Write a thin function that calls ``_run_query(session, _SQL_<NAME>, params)``.
3. Annotate with ``# type: ignore[return-value]`` if mypy complains about
   cursor row typing.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from owl.exceptions import AnalysisError
from owl.logger import get_logger

log = get_logger(__name__)


# ── Query helpers ──────────────────────────────────────────────────────────────

def _run_query(
    session: Session,
    sql: str,
    params: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Execute *sql* via *session* and return results as a DataFrame.

    Parameters
    ----------
    session:
        Active SQLAlchemy Session.
    sql:
        Raw SQL string with optional ``:named`` parameter placeholders.
    params:
        Dict of named parameters to bind.

    Returns
    -------
    pd.DataFrame

    Raises
    ------
    AnalysisError
        On any database or result-parsing error.
    """
    try:
        result = session.execute(text(sql), params or {})
        rows = result.fetchall()
        columns = list(result.keys())
        return pd.DataFrame(rows, columns=columns)
    except Exception as exc:
        raise AnalysisError(
            "SQL query execution failed.",
            context={"sql_snippet": sql[:200], "original_error": str(exc)},
        ) from exc


# ── Named queries ──────────────────────────────────────────────────────────────

_SQL_ATTENDANCE_SUMMARY = """
    SELECT
        e.employee_id,
        e.full_name,
        e.department,
        COUNT(*) FILTER (WHERE a.status = 'Present')  AS present_days,
        COUNT(*) FILTER (WHERE a.status = 'Absent')   AS absent_days,
        COUNT(*) FILTER (WHERE a.status = 'Leave')    AS leave_days,
        COUNT(*)                                       AS total_days
    FROM fact_attendance a
    JOIN dim_employee e ON e.id = a.employee_fk
    JOIN dim_date     d ON d.id = a.date_fk
    WHERE d.year  = :year
      AND d.month = :month
    GROUP BY e.employee_id, e.full_name, e.department
    ORDER BY e.full_name;
"""

_SQL_LEAVE_BREAKDOWN = """
    SELECT
        e.employee_id,
        e.full_name,
        lt.leave_type_name,
        COUNT(*) AS days_taken
    FROM fact_attendance a
    JOIN dim_employee  e  ON e.id  = a.employee_fk
    JOIN dim_leave_type lt ON lt.id = a.leave_type_fk
    WHERE a.status = 'Leave'
    GROUP BY e.employee_id, e.full_name, lt.leave_type_name
    ORDER BY e.full_name, lt.leave_type_name;
"""

_SQL_DEPARTMENT_ATTENDANCE_RATE = """
    SELECT
        e.department,
        d.year,
        d.month,
        ROUND(
            100.0 * COUNT(*) FILTER (WHERE a.status = 'Present') / NULLIF(COUNT(*), 0),
            2
        ) AS attendance_rate_pct
    FROM fact_attendance a
    JOIN dim_employee e ON e.id = a.employee_fk
    JOIN dim_date     d ON d.id = a.date_fk
    GROUP BY e.department, d.year, d.month
    ORDER BY d.year DESC, d.month DESC, e.department;
"""


# ── Public query functions ────────────────────────────────────────────────────

def get_monthly_attendance_summary(
    session: Session, year: int, month: int
) -> pd.DataFrame:
    """Return a per-employee attendance summary for a given month.

    Columns: employee_id, full_name, department,
             present_days, absent_days, leave_days, total_days.
    """
    log.info(f"Running attendance summary for {year}-{month:02d}.")
    return _run_query(session, _SQL_ATTENDANCE_SUMMARY, {"year": year, "month": month})


def get_leave_breakdown(session: Session) -> pd.DataFrame:
    """Return total leave days per employee per leave type (all time)."""
    log.info("Running leave breakdown query.")
    return _run_query(session, _SQL_LEAVE_BREAKDOWN)


def get_department_attendance_rates(session: Session) -> pd.DataFrame:
    """Return monthly attendance rate (%) grouped by department."""
    log.info("Running department attendance rates query.")
    return _run_query(session, _SQL_DEPARTMENT_ATTENDANCE_RATE)
