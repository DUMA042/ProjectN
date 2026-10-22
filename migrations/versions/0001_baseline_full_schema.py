"""Baseline: full schema as of R-01 (matches owl/load/schema.sql).

Fresh database:  `alembic upgrade head` builds everything (idempotent —
safe to run twice).
Existing database (pre-Alembic, e.g. flowdb): `alembic stamp 0001` marks the
baseline applied WITHOUT running it. Never run `upgrade` from empty on a
database that already has tables outside Alembic control.

Downgrade drops all application tables (test/disaster use only).

Revision ID: 0001
Revises:
Create Date: 2026-10-12
"""
from pathlib import Path
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SCHEMA_FILE = Path(__file__).resolve().parent.parent.parent / "owl" / "load" / "schema.sql"

# Managed tables, dependents first (downgrade order). Mirrors models metadata.
_MANAGED_TABLES = [
    "kanban_task_labels", "kanban_task_assignees", "kanban_task_history",
    "kanban_tasks", "kanban_labels", "kanban_columns", "kanban_boards",
    "quarantine_trainings", "quarantine_card_swipes",
    "file_ingestion_meta", "privacy_tokens",
    "attendance_daily",
    "employee_trainings", "leave_records", "leave_applications",
    "employee_location_history", "employee_rank_history",
    "employee_gl_history", "employee_department_history",
    "employee_card_swipes", "employees",
    "leave_types", "venues", "consultants", "units", "ranks",
    "locations", "employment_types", "employee_statuses",
    "grade_levels", "departments", "rules_settings",
]


def upgrade() -> None:
    """Execute schema.sql (idempotent: IF NOT EXISTS + guarded constraints)."""
    sql = _SCHEMA_FILE.read_text(encoding="utf-8")
    op.execute(sql)


def downgrade() -> None:
    """Drop all application tables. TEST/DISASTER USE ONLY — destroys data."""
    for table in _MANAGED_TABLES:
        op.execute(f"DROP TABLE IF EXISTS public.{table} CASCADE")
