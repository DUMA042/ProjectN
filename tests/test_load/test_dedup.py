"""Natural-key dedup: reprocessing identical content cannot duplicate rows.

Needs local PostgreSQL (throwaway flowdb_test); skips otherwise.
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parent.parent.parent
TEST_URL = "postgresql+psycopg2://postgres:1234@localhost:5433/flowdb_test"
ADMIN_URL = "postgresql+psycopg2://postgres:1234@localhost:5433/postgres"


def _admin(sql: str) -> None:
    engine = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        conn.execute(text(sql))
    engine.dispose()


def _alembic(*args: str) -> None:
    env = {**os.environ, "DATABASE_URL": TEST_URL}
    proc = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=ROOT, capture_output=True, text=True, env=env, timeout=300,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]


@pytest.fixture()
def test_db():
    try:
        _admin("SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
               "WHERE datname = 'flowdb_test' AND pid <> pg_backend_pid()")
        _admin("DROP DATABASE IF EXISTS flowdb_test")
        _admin("CREATE DATABASE flowdb_test")
    except Exception as exc:
        pytest.skip(f"local PostgreSQL unavailable: {exc}")
    _alembic("upgrade", "head")
    yield
    try:
        _admin("SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
               "WHERE datname = 'flowdb_test' AND pid <> pg_backend_pid()")
        _admin("DROP DATABASE IF EXISTS flowdb_test")
    except Exception:
        pass


def _session():
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(TEST_URL)
    return sessionmaker(bind=engine)()


def test_leave_reprocessing_is_idempotent(test_db):
    from owl.load.loader import DataLoader

    s = _session()
    try:
        s.execute(text("INSERT INTO employees (id_no, full_name) VALUES ('T1', 'Test One')"))
        s.execute(text("INSERT INTO leave_types (leave_type_name) VALUES ('Annual')"))
        s.commit()
        lt = s.execute(text("SELECT leave_type_id FROM leave_types WHERE leave_type_name='Annual'")).scalar()
        df = pd.DataFrame([{
            "id_no": "T1", "leave_type_id": lt,
            "start_date": date(2026, 6, 1), "end_date": date(2026, 6, 3),
        }])
        loader = DataLoader(s)
        loader.load({"leave_records": df})
        s.commit()
        loader.load({"leave_records": df})
        s.commit()
        n = s.execute(text("SELECT COUNT(*) FROM leave_records WHERE id_no='T1'")).scalar()
        assert n == 1
    finally:
        s.close()


def test_training_reprocessing_is_idempotent(test_db):
    from owl.load.loader import DataLoader

    s = _session()
    try:
        s.execute(text("INSERT INTO employees (id_no, full_name) VALUES ('T2', 'Test Two')"))
        s.execute(text("INSERT INTO venues (venue_name) VALUES ('Hall')"))
        s.execute(text("INSERT INTO consultants (consultant_name) VALUES ('Doc')"))
        s.commit()
        venue = s.execute(text("SELECT venue_id FROM venues WHERE venue_name='Hall'")).scalar()
        cons = s.execute(text("SELECT consultant_id FROM consultants WHERE consultant_name='Doc'")).scalar()
        df = pd.DataFrame([{
            "id_no": "T2", "venue_id": venue, "consultant_id": cons,
            "start_date": date(2026, 6, 1), "end_date": date(2026, 6, 2),
        }])
        loader = DataLoader(s)
        loader.load({"employee_trainings": df})
        s.commit()
        loader.load({"employee_trainings": df})
        s.commit()
        n = s.execute(text("SELECT COUNT(*) FROM employee_trainings WHERE id_no='T2'")).scalar()
        assert n == 1
    finally:
        s.close()
