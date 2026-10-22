"""Export the employee seed bundle used by the desktop installer.

Packaging-time tool. Writes CSV/JSON into a target directory that is
git-ignored (contains personal data — never commit it).

Usage:
    python scripts/export_seed.py --out seed

The produced bundle is loaded on first run by ``scripts/load_seed.py`` when the
employees table is empty.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd
from sqlalchemy import text

from owl.load.database import get_session

# (table, id column, name column) — import order matters (FKs).
LOOKUPS = [
    ("departments", "department_id", "department_name"),
    ("grade_levels", "gl_id", "gl_name"),
    ("ranks", "rank_id", "rank_name"),
    ("employee_statuses", "status_id", "status_name"),
    ("employment_types", "emp_type_id", "emp_type_name"),
    ("locations", "location_id", "location_name"),
    ("leave_types", "leave_type_id", "leave_type_name"),
]

EMPLOYEE_COLUMNS = [
    "id_no",
    "full_name",
    "sex",
    "rank_id",
    "emp_type_id",
    "status_id",
    "remark",
    "location_id",
    "department_id",
    "gl_id",
    "geographical_zone",
    "date_of_last_deployment",
    "phone_number",
]

REQUIRED_LEAVE_TYPES = {
    "PRE-RETIREMENT LEAVE",
    "ANNUAL",
    "CASUAL AFTER ANNUAL",
    "COMPASSIONATE",
    "PATERNITY",
    "MATERNITY",
    "SICK",
    "EXAM",
}


def export_bundle(out_dir: Path) -> dict:
    """Write the seed bundle. Returns the manifest (counts + timestamp)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}

    with get_session() as session:
        for table, id_col, name_col in LOOKUPS:
            frame = pd.read_sql(
                text(f"SELECT {id_col}, {name_col} FROM {table} ORDER BY {id_col}"),
                session.connection(),
            )
            frame.to_csv(out_dir / f"{table}.csv", index=False)
            counts[table] = int(len(frame))

        employees = pd.read_sql(
            text(
                "SELECT " + ", ".join(EMPLOYEE_COLUMNS)
                + " FROM employees ORDER BY id_no"
            ),
            session.connection(),
        )
        employees.to_csv(out_dir / "employees.csv", index=False)
        counts["employees"] = int(len(employees))
        counts["employees_with_phone"] = int(employees["phone_number"].notna().sum())

        rules = {
            row[0]: row[1]
            for row in session.execute(
                text("SELECT rule_key, rule_value FROM rules_settings")
            )
        }
        (out_dir / "rules.json").write_text(
            json.dumps(rules, indent=2, sort_keys=True), encoding="utf-8"
        )
        counts["rules"] = len(rules)

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": counts,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    return manifest


def validate_bundle(out_dir: Path) -> list[str]:
    """Return human-readable problems with the bundle (empty = valid)."""
    problems: list[str] = []
    required = ["employees.csv", "rules.json", *(f"{t}.csv" for t, _, _ in LOOKUPS)]
    for name in required:
        if not (out_dir / name).exists():
            problems.append(f"missing file: {name}")
    if problems:
        return problems

    employees = pd.read_csv(out_dir / "employees.csv", dtype=str, keep_default_na=False)
    if employees.empty:
        problems.append("employees.csv is empty")
    if employees["id_no"].duplicated().any():
        problems.append("employees.csv contains duplicate id_no values")

    leave_types = pd.read_csv(out_dir / "leave_types.csv", dtype=str)
    present = set(leave_types["leave_type_name"].str.strip())
    missing = REQUIRED_LEAVE_TYPES - present
    if missing:
        problems.append(f"leave_types missing required entries: {sorted(missing)}")

    rules = json.loads((out_dir / "rules.json").read_text(encoding="utf-8"))
    for key in (
        "working_hours",
        "incomplete_threshold",
        "holidays",
        "eligible_statuses",
        "leave_overrides_training",
    ):
        if key not in rules:
            problems.append(f"rules.json missing '{key}'")

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Export the employee seed bundle")
    parser.add_argument("--out", default="seed", help="target directory (git-ignored)")
    args = parser.parse_args()

    out_dir = Path(args.out)
    manifest = export_bundle(out_dir)
    problems = validate_bundle(out_dir)

    print(f"Seed bundle written to {out_dir.resolve()}")
    for key, value in manifest["counts"].items():
        print(f"  {key}: {value}")

    if problems:
        print("\nBUNDLE INVALID:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    print("\nBundle valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
