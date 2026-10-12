"""Converge pre-Alembic databases: dedup unique indexes (guarded no-ops).

Fresh databases already have these via the 0001 baseline. Existing installs
built before the uniques existed get them here. Guards make this safe to run
anywhere, any number of times. If duplicate business rows exist, the CREATE
fails loudly with the offending key — clean the data, then re-run; nothing
is deleted automatically.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-12
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEXES = {
    "uk_leave_records_dedup": (
        "public.leave_records (id_no, leave_type_id, start_date, end_date)"
    ),
    "uk_employee_trainings_dedup": (
        "public.employee_trainings (id_no, venue_id, consultant_id, start_date, end_date)"
    ),
}


def upgrade() -> None:
    """Create missing dedup unique indexes (no-op where present)."""
    for name, target in _INDEXES.items():
        op.execute(
            f"DO $$ BEGIN "
            f"IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = '{name}') THEN "
            f"CREATE UNIQUE INDEX {name} ON {target}; "
            f"END IF; "
            f"END $$;"
        )


def downgrade() -> None:
    """Drop the dedup unique indexes (data untouched)."""
    for name in _INDEXES:
        op.execute(f"DROP INDEX IF EXISTS public.{name}")
