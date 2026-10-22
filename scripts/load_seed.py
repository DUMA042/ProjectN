"""Load the employee seed bundle on first run (desktop installer).

Idempotent by design: does nothing when the employees table already has rows,
so it can never overwrite edits or re-seed after an upgrade.

Usage:
    python scripts/load_seed.py --dir seed
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd
from sqlalchemy import text

from owl.load.database import get_session
from scripts.export_seed import EMPLOYEE_COLUMNS, LOOKUPS

# Nullable text columns: an empty CSV cell means NULL, not "".
NULLABLE_TEXT = {"sex", "remark", "geographical_zone", "phone_number"}
INT_COLUMNS = {"rank_id", "emp_type_id", "status_id", "location_id", "department_id", "gl_id"}
DATE_COLUMNS = {"date_of_last_deployment"}


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _cell(value: str) -> str | None:
    value = (value or "").strip()
    return value or None


def _as_int(value: str) -> int | None:
    cell = _cell(value)
    return int(cell) if cell is not None else None


def _as_date(value: str) -> date | None:
    cell = _cell(value)
    return date.fromisoformat(cell) if cell is not None else None


def _employee_row(record: dict) -> dict:
    row: dict = {}
    for column in EMPLOYEE_COLUMNS:
        raw = record.get(column, "")
        if column in INT_COLUMNS:
            row[column] = _as_int(raw)
        elif column in DATE_COLUMNS:
            row[column] = _as_date(raw)
        elif column in NULLABLE_TEXT:
            row[column] = _cell(raw)
        else:
            row[column] = (raw or "").strip()
    return row


def seed_if_empty(bundle_dir: Path) -> dict:
    """Load the bundle only when no employees exist. Returns a summary."""
    bundle_dir = Path(bundle_dir)
    if not (bundle_dir / "manifest.json").exists():
        return {"skipped": True, "reason": "no seed bundle"}

    with get_session() as session:
        existing = session.execute(text("SELECT COUNT(*) FROM employees")).scalar()
        if existing:
            return {"skipped": True, "reason": "employees already present", "employees": int(existing)}

        summary: dict[str, int] = {}

        # 1. Lookups with explicit ids (stable across the seed and later uploads).
        for table, id_col, name_col in LOOKUPS:
            frame = _read_csv(bundle_dir / f"{table}.csv")
            records = [
                {id_col: int(row[id_col]), name_col: str(row[name_col])}
                for _, row in frame.iterrows()
            ]
            if records:
                session.execute(
                    text(
                        f"INSERT INTO {table} ({id_col}, {name_col}) "
                        f"VALUES (:{id_col}, :{name_col}) "
                        f"ON CONFLICT ({id_col}) DO NOTHING"
                    ),
                    records,
                )
                session.execute(
                    text(
                        f"SELECT setval(pg_get_serial_sequence('{table}', '{id_col}'), "
                        f"(SELECT MAX({id_col}) FROM {table}))"
                    )
                )
            summary[table] = len(records)

        # 2. Employees (natural key id_no).
        employees = _read_csv(bundle_dir / "employees.csv")
        rows = [_employee_row(record) for record in employees.to_dict(orient="records")]
        if rows:
            placeholders = ", ".join(f":{c}" for c in EMPLOYEE_COLUMNS)
            columns = ", ".join(EMPLOYEE_COLUMNS)
            session.execute(
                text(
                    f"INSERT INTO employees ({columns}) VALUES ({placeholders}) "
                    f"ON CONFLICT (id_no) DO NOTHING"
                ),
                rows,
            )
        summary["employees"] = len(rows)

        # 3. Rules: only fill missing keys, never overwrite operator settings.
        rules = json.loads((bundle_dir / "rules.json").read_text(encoding="utf-8"))
        for key, value in rules.items():
            session.execute(
                text(
                    "INSERT INTO rules_settings (rule_key, rule_value) "
                    "VALUES (:k, CAST(:v AS jsonb)) ON CONFLICT (rule_key) DO NOTHING"
                ),
                {"k": key, "v": json.dumps(value)},
            )
        summary["rules"] = len(rules)

        # 4. Flush the rules cache so the first requests see the seeded values.
        try:
            from owl.rules.engine import invalidate_rules_cache

            invalidate_rules_cache()
        except Exception:  # noqa: BLE001 — cache is best-effort here
            pass

    return {"skipped": False, "seeded": summary}


def main() -> int:
    parser = argparse.ArgumentParser(description="Load the employee seed bundle")
    parser.add_argument("--dir", default="seed", help="bundle directory")
    args = parser.parse_args()

    result = seed_if_empty(Path(args.dir))
    if result.get("skipped"):
        print(f"Seed skipped: {result.get('reason')}")
        return 0

    print("Seed applied:")
    for key, value in result["seeded"].items():
        print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
