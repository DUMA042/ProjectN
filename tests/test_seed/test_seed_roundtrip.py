"""Install-seed validation: export from live data, load into a fresh schema.

This is the gate promised before an installer is built: a throwaway database
must end up with the same employee/lookup counts as the source, required leave
types present, and no runtime artefacts (tokens, history) seeded.

Needs local PostgreSQL; skips otherwise. Production data is only read.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

ADMIN_URL = "postgresql+psycopg2://postgres:1234@localhost:5433/postgres"
LIVE_URL = "postgresql+psycopg2://postgres:1234@localhost:5433/flowdb"
TEST_DB = "flowdb_seedtest"
TEST_URL = f"postgresql+psycopg2://postgres:1234@localhost:5433/{TEST_DB}"


def _admin(sql: str) -> None:
    engine = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        conn.execute(text(sql))
    engine.dispose()


def _drop_test_db() -> None:
    _admin(
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
        f"WHERE datname = '{TEST_DB}' AND pid <> pg_backend_pid()"
    )
    _admin(f"DROP DATABASE IF EXISTS {TEST_DB}")


def _run(script: str, *args: str, env_extra: dict | None = None) -> str:
    env = {**os.environ, **(env_extra or {})}
    proc = subprocess.run(
        [sys.executable, script, *args],
        cwd=ROOT, capture_output=True, text=True, env=env, timeout=600,
    )
    assert proc.returncode == 0, (proc.stdout[-3000:], proc.stderr[-3000:])
    return proc.stdout


def _scalar(url: str, sql: str):
    engine = create_engine(url, poolclass=NullPool)
    try:
        with engine.connect() as conn:
            return conn.execute(text(sql)).scalar()
    finally:
        engine.dispose()


def _column(url: str, sql: str) -> set[str]:
    engine = create_engine(url, poolclass=NullPool)
    try:
        with engine.connect() as conn:
            return {row[0] for row in conn.execute(text(sql))}
    finally:
        engine.dispose()


@pytest.fixture()
def bundle(tmp_path):
    """Export from the live database (skips if it has no employees)."""
    try:
        if not _scalar(LIVE_URL, "SELECT COUNT(*) FROM employees"):
            pytest.skip("live database has no employees")
    except Exception as exc:
        pytest.skip(f"local PostgreSQL unavailable: {exc}")

    out = tmp_path / "seed"
    _run("scripts/export_seed.py", "--out", str(out))
    return out


@pytest.fixture()
def fresh_db():
    try:
        _drop_test_db()
        _admin(f"CREATE DATABASE {TEST_DB}")
    except Exception as exc:
        pytest.skip(f"local PostgreSQL unavailable: {exc}")
    env = {**os.environ, "DATABASE_URL": TEST_URL}
    proc = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT, capture_output=True, text=True, env=env, timeout=600,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    yield
    try:
        _drop_test_db()
    except Exception:
        pass


def test_seed_loads_expected_counts(bundle, fresh_db):
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    expected = manifest["counts"]

    _run("scripts/load_seed.py", "--dir", str(bundle), env_extra={"DATABASE_URL": TEST_URL})

    checks = {
        "employees": "SELECT COUNT(*) FROM employees",
        "departments": "SELECT COUNT(*) FROM departments",
        "grade_levels": "SELECT COUNT(*) FROM grade_levels",
        "ranks": "SELECT COUNT(*) FROM ranks",
        "employee_statuses": "SELECT COUNT(*) FROM employee_statuses",
        "employment_types": "SELECT COUNT(*) FROM employment_types",
        "locations": "SELECT COUNT(*) FROM locations",
        "leave_types": "SELECT COUNT(*) FROM leave_types",
        "rules": "SELECT COUNT(*) FROM rules_settings",
        "employees_with_phone": (
            "SELECT COUNT(*) FROM employees WHERE phone_number IS NOT NULL "
            "AND phone_number <> ''"
        ),
    }
    for key, sql in checks.items():
        assert _scalar(TEST_URL, sql) == expected[key], key


def test_seed_is_idempotent(bundle, fresh_db):
    _run("scripts/load_seed.py", "--dir", str(bundle), env_extra={"DATABASE_URL": TEST_URL})
    before = _scalar(TEST_URL, "SELECT COUNT(*) FROM employees")
    out = _run(
        "scripts/load_seed.py", "--dir", str(bundle), env_extra={"DATABASE_URL": TEST_URL}
    )
    assert "skipped" in out.lower()
    assert _scalar(TEST_URL, "SELECT COUNT(*) FROM employees") == before


def test_seed_leaves_runtime_tables_empty(bundle, fresh_db):
    _run("scripts/load_seed.py", "--dir", str(bundle), env_extra={"DATABASE_URL": TEST_URL})
    for table in (
        "privacy_tokens",
        "employee_card_swipes",
        "leave_records",
        "employee_trainings",
        "attendance_daily",
        "employee_department_history",
    ):
        assert _scalar(TEST_URL, f"SELECT COUNT(*) FROM {table}") == 0, table


def test_required_leave_types_present(bundle, fresh_db):
    _run("scripts/load_seed.py", "--dir", str(bundle), env_extra={"DATABASE_URL": TEST_URL})
    names = _column(TEST_URL, "SELECT leave_type_name FROM leave_types")
    required = {
        "PRE-RETIREMENT LEAVE", "ANNUAL", "CASUAL AFTER ANNUAL", "COMPASSIONATE",
        "PATERNITY", "MATERNITY", "SICK", "EXAM",
    }
    assert required <= names
