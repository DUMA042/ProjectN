"""
scripts/migrate_nominal_schema.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
One-time schema migration for the Nominal Roll major update.

Changes applied:
  1. ADD employees.geographical_zone VARCHAR(100)
  2. ADD employees.date_of_last_deployment DATE
  3. ADD employees.phone_number VARCHAR(30)
  4. DROP FK employees_unit_id_fkey (if exists)
  5. DROP employees.unit_id column
  6. DROP TABLE employee_unit_history
  7. DROP employees.serial_no column

Safety:
  - All ADD operations check column existence first
  - All DROP operations use IF EXISTS
  - The script is idempotent (safe to re-run)
  - Dry-run mode: python scripts/migrate_nominal_schema.py --dry-run

Usage:
  python scripts/migrate_nominal_schema.py
  python scripts/migrate_nominal_schema.py --dry-run
"""

from __future__ import annotations

import sys
import argparse
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import psycopg2
from owl.config import settings


def _parse_dsn(database_url: str) -> dict:
    """Parse a SQLAlchemy URL into psycopg2 connect kwargs."""
    url = database_url.replace("postgresql+psycopg2://", "postgresql://")
    import urllib.parse as up
    p = up.urlparse(url)
    return {
        "dbname": p.path.lstrip("/"),
        "user": p.username,
        "password": p.password,
        "host": p.hostname,
        "port": p.port or 5432,
    }


# Each step has:
#   description    : human-readable label
#   check_sql      : SELECT that returns a row if the thing EXISTS
#   sql            : DDL to execute
#   run_when_found : if True, run SQL when check returns a row (e.g. "drop if found")
#                    if False, run SQL when check returns NO row (e.g. "add if absent")
MIGRATION_STEPS = [
    {
        "description": "ADD employees.geographical_zone VARCHAR(100)",
        "check_sql": (
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name='employees' "
            "AND column_name='geographical_zone'"
        ),
        "sql": "ALTER TABLE employees ADD COLUMN geographical_zone VARCHAR(100);",
        "run_when_found": False,
        "skip_msg": "geographical_zone already exists",
    },
    {
        "description": "ADD employees.date_of_last_deployment DATE",
        "check_sql": (
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name='employees' "
            "AND column_name='date_of_last_deployment'"
        ),
        "sql": "ALTER TABLE employees ADD COLUMN date_of_last_deployment DATE;",
        "run_when_found": False,
        "skip_msg": "date_of_last_deployment already exists",
    },
    {
        "description": "ADD employees.phone_number VARCHAR(30)",
        "check_sql": (
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name='employees' "
            "AND column_name='phone_number'"
        ),
        "sql": "ALTER TABLE employees ADD COLUMN phone_number VARCHAR(30);",
        "run_when_found": False,
        "skip_msg": "phone_number already exists",
    },
    {
        "description": "DROP FK constraint employees_unit_id_fkey (if it exists)",
        "check_sql": (
            "SELECT 1 FROM information_schema.table_constraints "
            "WHERE constraint_schema='public' "
            "AND constraint_name='employees_unit_id_fkey'"
        ),
        "sql": "ALTER TABLE employees DROP CONSTRAINT IF EXISTS employees_unit_id_fkey;",
        "run_when_found": True,
        "skip_msg": "employees_unit_id_fkey does not exist",
    },
    {
        "description": "DROP employees.unit_id column",
        "check_sql": (
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name='employees' "
            "AND column_name='unit_id'"
        ),
        "sql": "ALTER TABLE employees DROP COLUMN IF EXISTS unit_id;",
        "run_when_found": True,
        "skip_msg": "unit_id is already absent from employees",
    },
    {
        "description": "DROP TABLE employee_unit_history",
        "check_sql": (
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name='employee_unit_history'"
        ),
        "sql": "DROP TABLE IF EXISTS employee_unit_history CASCADE;",
        "run_when_found": True,
        "skip_msg": "employee_unit_history already absent",
    },
    {
        "description": "DROP employees.serial_no column",
        "check_sql": (
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name='employees' "
            "AND column_name='serial_no'"
        ),
        "sql": "ALTER TABLE employees DROP COLUMN IF EXISTS serial_no;",
        "run_when_found": True,
        "skip_msg": "serial_no is already absent from employees",
    },
]

VERIFY_COLS_SQL = """
SELECT column_name, data_type, character_maximum_length
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'employees'
ORDER BY ordinal_position;
"""


def run_migration(dry_run: bool = False) -> None:
    dsn = _parse_dsn(settings.get_database_url())
    conn = psycopg2.connect(**dsn)
    conn.autocommit = False
    cur = conn.cursor()

    prefix = "[DRY RUN] " if dry_run else ""
    print(f"\n{prefix}Nominal Roll Schema Migration")
    print("=" * 60)

    try:
        for step in MIGRATION_STEPS:
            desc = step["description"]
            check_sql = step["check_sql"]
            migration_sql = step["sql"]
            skip_msg = step["skip_msg"]
            run_when_found = step["run_when_found"]

            cur.execute(check_sql)
            found = cur.fetchone() is not None
            should_run = found if run_when_found else not found

            if not should_run:
                print(f"  [SKIP] {desc}")
                print(f"         ({skip_msg})")
                continue

            print(f"  [RUN]  {desc}")
            print(f"         SQL: {migration_sql.strip()}")
            if not dry_run:
                cur.execute(migration_sql)

        if not dry_run:
            conn.commit()
            print("\n[OK] Migration committed successfully.")
        else:
            print("\n[DRY RUN] No changes were applied.")

        # -- Verification -------------------------------------------------
        print("\nVerification - employees table columns after migration:")
        cur.execute(VERIFY_COLS_SQL)
        rows = cur.fetchall()
        for r in rows:
            print(f"  {r[0]:<35} {r[1]:<20} {r[2] or ''}")

        expected_absent = {"serial_no", "unit_id"}
        expected_present = {"geographical_zone", "date_of_last_deployment", "phone_number"}
        actual_cols = {r[0] for r in rows}

        print("\nColumn presence checks:")
        all_ok = True
        for col in expected_absent:
            if col in actual_cols:
                print(f"  [FAIL] '{col}' is still present (should be absent)")
                all_ok = False
            else:
                print(f"  [PASS] '{col}' is absent")

        for col in expected_present:
            if col not in actual_cols:
                print(f"  [FAIL] '{col}' is missing (should be present)")
                all_ok = False
            else:
                print(f"  [PASS] '{col}' is present")

        print("\nTable presence check:")
        cur.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name='employee_unit_history'"
        )
        if cur.fetchone():
            print("  [FAIL] employee_unit_history still exists")
            all_ok = False
        else:
            print("  [PASS] employee_unit_history is absent")

        if all_ok:
            print("\n[RESULT] All checks passed. Schema is correct.")
        else:
            print("\n[RESULT] WARNING: Some checks failed. Review output above.")

    except Exception as exc:
        conn.rollback()
        print(f"\n[ERROR] Migration FAILED and was rolled back: {exc}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nominal Roll schema migration")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be done without making any changes",
    )
    args = parser.parse_args()
    run_migration(dry_run=args.dry_run)
