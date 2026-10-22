"""Fact-rebuild single-flight: concurrent rebuilds serialize, table intact.

Needs local PostgreSQL; skips otherwise. Read-only except the lock itself:
the contended rebuild must return before TRUNCATE.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from owl.analytics.fact import _FACT_LOCK_KEY, rebuild_attendance_daily
from owl.load.database import get_engine


def _pg():
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as exc:
        pytest.skip(f"local PostgreSQL unavailable: {exc}")


def test_contended_rebuild_returns_already_running():
    engine = _pg()
    with engine.connect() as conn:
        before = conn.execute(text("SELECT COUNT(*) FROM attendance_daily")).scalar()
        conn.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _FACT_LOCK_KEY})
        try:
            result = rebuild_attendance_daily()
        finally:
            conn.rollback()
    assert result["status"] == "already_running"
    with engine.connect() as conn:
        after = conn.execute(text("SELECT COUNT(*) FROM attendance_daily")).scalar()
    assert before == after


def test_rebuild_result_carries_status():
    engine = _pg()
    with engine.connect() as conn:
        conn.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _FACT_LOCK_KEY})
        try:
            result = rebuild_attendance_daily()
        finally:
            conn.rollback()
    assert set(result) >= {"rows", "start", "end", "status", "unclassified"}
