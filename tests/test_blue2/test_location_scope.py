"""Location/department-scoped queries must not break the read-only fence.

Regression: _semantic_check opens a transaction on the shared session before
run_validated issues SET TRANSACTION READ ONLY. Postgres rejects a SET that
is not the first statement of the transaction (ActiveSqlTransaction / 25001),
which used to surface as mode="error" for ANY location/department-filtered
question. run_validated must close the pre-opened transaction first.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from owl.ai import pipeline, secure_execute
from owl.load.database import get_session


def _hq_exists(session) -> bool:
    return session.execute(
        text("SELECT 1 FROM locations WHERE LOWER(location_name) = 'hq'")
    ).first() is not None


def test_run_validated_after_preopened_transaction():
    """run_validated survives a session that already ran queries (no PII)."""
    with get_session() as s:
        assert _hq_exists(s), "test fixture needs an HQ location"
        # Simulate _semantic_check: a real SELECT that autobegins a txn.
        s.execute(text("SELECT 1 FROM locations WHERE LOWER(location_name) = 'hq'"))
        assert s.in_transaction()
        sql = (
            'SELECT e.full_name AS "full_name", ad.checkin_time AS "checkin_time" '
            "FROM attendance_daily ad JOIN employees e ON e.id_no = ad.id_no "
            "LEFT JOIN locations l ON e.location_id = l.location_id "
            "WHERE (COALESCE(l.location_name, 'Unknown')) = :p0 "
            "ORDER BY ad.checkin_time DESC LIMIT :p1 OFFSET :p2"
        )
        from owl.ai import catalog as catalog_module

        result = secure_execute.run_validated(
            s, sql, {"p0": "HQ", "p1": 5, "p2": 0},
            tables={"attendance_daily", "employees", "locations"},
            columns=catalog_module.bare_columns(),
            aliases={"ad", "e", "l", "full_name", "checkin_time"},
        )
        assert "rows" in result and "columns" in result
        assert result["row_count"] == len(result["rows"])


def test_location_scoped_late_question_returns_data():
    """End-to-end: the reported failing shape answers with data, not error."""
    with get_session() as s:
        if not _hq_exists(s):
            pytest.skip("no HQ location in fixture data")
        result = pipeline.run_ask(
            s, "top 5 staff that came late at HQ",
        )
        assert result["mode"] == "data", result.get("answer")
        assert result["row_count"] > 0
