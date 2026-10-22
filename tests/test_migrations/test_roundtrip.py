"""Migration round-trip on a throwaway database (needs local PostgreSQL).

Skips cleanly when Postgres is unreachable. Never touches flowdb: every
command carries an explicit DATABASE_URL for flowdb_test only.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

ROOT = Path(__file__).resolve().parent.parent.parent
TEST_URL = "postgresql+psycopg2://postgres:1234@localhost:5433/flowdb_test"
ADMIN_URL = "postgresql+psycopg2://postgres:1234@localhost:5433/postgres"


def _admin(sql: str) -> None:
    engine = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        conn.execute(text(sql))
    engine.dispose()


def _drop_test_db() -> None:
    _admin(
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
        "WHERE datname = 'flowdb_test' AND pid <> pg_backend_pid()"
    )
    _admin("DROP DATABASE IF EXISTS flowdb_test")


def _alembic(*args: str) -> str:
    env = {**os.environ, "DATABASE_URL": TEST_URL}
    proc = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=ROOT, capture_output=True, text=True, env=env, timeout=300,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    return proc.stdout


def _state():
    engine = create_engine(TEST_URL, poolclass=NullPool)
    with engine.connect() as conn:
        tables = conn.execute(
            text("select count(*) from information_schema.tables "
                 "where table_schema='public' and table_type='BASE TABLE'")
        ).scalar()
        uniques = conn.execute(
            text("select count(*) from pg_class where relname in "
                 "('uk_leave_records_dedup','uk_employee_trainings_dedup')")
        ).scalar()
        version = conn.execute(text("select version_num from alembic_version")).scalar()
    engine.dispose()
    return tables, uniques, version


@pytest.fixture()
def fresh_db():
    try:
        _drop_test_db()
        _admin("CREATE DATABASE flowdb_test")
    except Exception as exc:
        pytest.skip(f"local PostgreSQL unavailable: {exc}")
    yield
    try:
        _drop_test_db()
    except Exception:
        pass


def _init_db() -> None:
    env = {**os.environ, "DATABASE_URL": TEST_URL}
    proc = subprocess.run(
        [sys.executable, "scripts/init_db.py"],
        cwd=ROOT, capture_output=True, text=True, env=env, timeout=300,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]


def test_init_twice_then_stamp_upgrade(fresh_db):
    # init_db (raw schema.sql) must be safely re-runnable — the R-01 fix.
    _init_db()
    _init_db()
    _alembic("stamp", "0001")
    _alembic("upgrade", "head")
    tables, uniques, version = _state()
    assert tables >= 32 and uniques == 2 and version == "0002"


def test_upgrade_head_downgrade_cycle(fresh_db):
    _alembic("upgrade", "head")
    tables, uniques, version = _state()
    assert tables >= 32 and uniques == 2 and version == "0002"
    _alembic("downgrade", "-1")
    assert _state()[1] == 0
    _alembic("upgrade", "head")
    assert _state() == (tables, 2, "0002")
