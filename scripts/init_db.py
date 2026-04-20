"""
scripts/init_db.py
~~~~~~~~~~~~~~~~~~
One-time (idempotent) database initialisation script.

Reads ``owl/load/schema.sql`` and executes it against the configured database.
Safe to run multiple times — all DDL uses ``CREATE TABLE IF NOT EXISTS``.

Usage
-----
    python scripts/init_db.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is on sys.path when run directly.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from sqlalchemy import text

from owl.load.database import get_engine, verify_connection
from owl.logger import get_logger

log = get_logger(__name__)

_SCHEMA_FILE = _PROJECT_ROOT / "owl" / "load" / "schema.sql"


def init_db() -> None:
    """Execute schema.sql against the configured PostgreSQL database."""
    log.info("Verifying database connection…")
    verify_connection()

    if not _SCHEMA_FILE.exists():
        log.error(f"Schema file not found: {_SCHEMA_FILE}")
        sys.exit(1)

    sql = _SCHEMA_FILE.read_text(encoding="utf-8")
    log.info(f"Executing schema from: {_SCHEMA_FILE.name}")

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(sql))

    log.info("Database initialisation complete.")


if __name__ == "__main__":
    init_db()
