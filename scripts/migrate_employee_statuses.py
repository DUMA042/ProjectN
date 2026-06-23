"""
scripts/migrate_employee_statuses.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
One-time migration — replaces old employee_statuses with the authoritative 11.
Run once:  python scripts/migrate_employee_statuses.py
After running, re-process the Nominal Roll to re-map employees to new status IDs.

Effect
------
1. DELETE all rows from employee_statuses
   → cascades to NULL on employees.status_id (ON DELETE SET NULL)
2. RESET the auto-increment sequence
3. INSERT the 11 authoritative statuses
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from sqlalchemy import text
from owl.load.database import get_session
from owl.load.models import EmployeeStatus
from owl.logger import get_logger

log = get_logger(__name__)

NEW_STATUSES = [
    "Active",
    "Disciplinary matters",
    "Leave of Absence",
    "Medical",
    "on Training",
    "Resignation",
    "salary Stoppage",
    "Sea time training",
    "Secondment",
    "Secondment on National interest",
    "Study Leave",
]


def migrate() -> None:
    with get_session() as session:
        # 1. Clear old statuses
        deleted = session.execute(text("DELETE FROM employee_statuses")).rowcount
        log.info(f"Deleted {deleted} old status row(s).")

        # 2. Reset sequence
        session.execute(
            text("ALTER SEQUENCE employee_statuses_status_id_seq RESTART WITH 1")
        )

        # 3. Insert new statuses
        for name in NEW_STATUSES:
            session.add(EmployeeStatus(status_name=name))

        session.commit()
        log.info(f"Inserted {len(NEW_STATUSES)} new statuses.")
        for name in NEW_STATUSES:
            log.info(f"  - {name}")

    log.info("Migration complete. Re-process Nominal Roll to remap employees.")


if __name__ == "__main__":
    migrate()
