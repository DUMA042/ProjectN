"""Alembic environment: URL + metadata come from the app's own config/models.

Usage
-----
Fresh database:   alembic upgrade head        (baseline builds the schema)
Existing database (pre-Alembic, e.g. flowdb):
                  alembic stamp 0001          (mark baseline applied — the
                  schema is already there; do NOT run upgrade on it)
Next change:      alembic revision -m "..."   (autogenerate against models)

The URL defaults to settings (env DATABASE_URL); override per-invocation
with ``alembic -x db_url=<url> upgrade head`` (used by migration tests).
"""
from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import create_engine

from alembic import context

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from owl.load.models import Base  # noqa: E402

target_metadata = Base.metadata

# Tables managed outside the ORM (built by application code, not models).
# Autogenerate must never try to create or drop these.
UNMANAGED_TABLES = frozenset({"attendance_daily"})


def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and name in UNMANAGED_TABLES:
        return False
    return True


def _db_url() -> str:
    override = context.get_x_argument(as_dictionary=True).get("db_url")
    if override:
        return override
    from owl.config import settings  # noqa: E402

    url = settings.get_database_url()
    if not url:
        raise RuntimeError("No database URL: set DATABASE_URL or pass -x db_url=<url>")
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=_db_url(),
        target_metadata=target_metadata,
        include_object=include_object,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_db_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
