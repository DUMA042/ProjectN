"""Models-vs-DDL drift guard: the reconciliation R-01 performed must hold.

attendance_daily is intentionally model-less (built by application code);
env.py excludes it from autogenerate.
"""
from __future__ import annotations

import re
from pathlib import Path

SCHEMA = Path(__file__).resolve().parent.parent.parent / "owl" / "load" / "schema.sql"

# Parser noise, not real columns.
_NOISE = {"CONSTRAINT"}


def _ddl_tables() -> dict[str, set[str]]:
    ddl = SCHEMA.read_text(encoding="utf-8")
    out = {}
    for m in re.finditer(r"CREATE TABLE IF NOT EXISTS public\.(\w+)\s*\((.*?)\n\);", ddl, re.DOTALL):
        cols = set(re.findall(r"^\s{4}(\"?\w+\"?)\s", m.group(2), re.MULTILINE))
        out[m.group(1)] = {c.strip('"') for c in cols} - _NOISE
    return out


def test_table_sets_match():
    from owl.load.models import Base

    dtables = _ddl_tables()
    mtables = {t.name for t in Base.metadata.tables.values()}
    assert set(dtables) - mtables == {"attendance_daily"}
    assert mtables - set(dtables) == set()


def test_dedup_uniques_present_both_sides():
    from owl.load.models import Base

    ddl = SCHEMA.read_text(encoding="utf-8")
    assert "uk_leave_records_dedup" in ddl
    assert "uk_employee_trainings_dedup" in ddl
    leave = Base.metadata.tables["leave_records"]
    training = Base.metadata.tables["employee_trainings"]
    leave_names = {c.name for c in leave.constraints if getattr(c, "name", "")}
    training_names = {c.name for c in training.constraints if getattr(c, "name", "")}
    assert "uk_leave_records_dedup" in leave_names
    assert "uk_employee_trainings_dedup" in training_names


def test_constraint_guards_present():
    """Every ADD CONSTRAINT must sit inside an IF NOT EXISTS guard so
    schema.sql (and init_db) re-runs safely."""
    ddl = SCHEMA.read_text(encoding="utf-8")
    bare = re.findall(r"^ALTER TABLE\b.*ADD CONSTRAINT", ddl, re.MULTILINE)
    assert bare == []
    guards = re.findall(r"pg_constraint WHERE conname = '(\w+)'", ddl)
    assert len(guards) >= 30
