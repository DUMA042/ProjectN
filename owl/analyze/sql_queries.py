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
# All queries target the actual schema (employees, departments, leave_records, etc.)
# — no star-schema tables (dim_*, fact_*) are assumed.

_SQL_DASHBOARD_SUMMARY = """
    SELECT
        (SELECT COUNT(*) FROM employees) AS total_employees,
        (SELECT COUNT(*) FROM employees e
         JOIN employee_statuses s ON e.status_id = s.status_id
         WHERE LOWER(s.status_name) = 'active') AS active_employees,
        (SELECT COUNT(DISTINCT lr.id_no) FROM leave_records lr
         WHERE CURRENT_DATE BETWEEN lr.start_date AND COALESCE(lr.end_date, lr.start_date)) AS staff_on_leave,
        (SELECT COUNT(DISTINCT et.id_no) FROM employee_trainings et
         WHERE CURRENT_DATE BETWEEN et.start_date AND et.end_date) AS staff_in_training
"""

_SQL_DEPARTMENT_DISTRIBUTION = """
    SELECT
        COALESCE(d.department_name, 'Unknown') AS department_name,
        COUNT(e.id_no) AS employee_count
    FROM employees e
    LEFT JOIN departments d ON e.department_id = d.department_id
    GROUP BY d.department_name
    ORDER BY employee_count DESC
"""

_SQL_RECENT_INGESTIONS = """
    SELECT
        id::TEXT,
        original_filename,
        normalized_filename,
        report_type,
        status,
        error_context,
        created_at,
        processed_at
    FROM file_ingestion_meta
    ORDER BY created_at DESC
    LIMIT :limit
"""

_SQL_LEAVE_BREAKDOWN_BY_TYPE = """
    SELECT
        lt.leave_type_name,
        COUNT(lr.record_id) AS total_entries,
        COUNT(DISTINCT lr.id_no) AS unique_staff
    FROM leave_records lr
    JOIN leave_types lt ON lr.leave_type_id = lt.leave_type_id
    GROUP BY lt.leave_type_name
    ORDER BY total_entries DESC
"""

_SQL_STATUS_DISTRIBUTION = """
    SELECT
        es.status_name,
        COUNT(e.id_no) AS employee_count
    FROM employees e
    JOIN employee_statuses es ON e.status_id = es.status_id
    GROUP BY es.status_name
    ORDER BY employee_count DESC
"""


# ── Public query functions ────────────────────────────────────────────────────

def get_dashboard_summary(session: Session) -> pd.DataFrame:
    """Return single-row dashboard KPIs: total, active, on leave, in training."""
    log.info("Running dashboard summary query.")
    return _run_query(session, _SQL_DASHBOARD_SUMMARY)


def get_department_distribution(session: Session) -> pd.DataFrame:
    """Return employee count per department, ordered by count descending."""
    log.info("Running department distribution query.")
    return _run_query(session, _SQL_DEPARTMENT_DISTRIBUTION)


def get_recent_ingestions(session: Session, limit: int = 20) -> pd.DataFrame:
    """Return the most recent file ingestion records."""
    log.info(f"Running recent ingestions query (limit={limit}).")
    return _run_query(session, _SQL_RECENT_INGESTIONS, {"limit": limit})


def get_leave_breakdown_by_type(session: Session) -> pd.DataFrame:
    """Return leave entries and unique staff counts per leave type."""
    log.info("Running leave breakdown by type query.")
    return _run_query(session, _SQL_LEAVE_BREAKDOWN_BY_TYPE)


def get_status_distribution(session: Session) -> pd.DataFrame:
    """Return employee count per status category."""
    log.info("Running status distribution query.")
    return _run_query(session, _SQL_STATUS_DISTRIBUTION)
