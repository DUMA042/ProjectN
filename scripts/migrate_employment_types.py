"""
scripts/migrate_employment_types.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
One-time migration — inserts missing employment types discovered from Nominal Roll data.
Run once:  python scripts/migrate_employment_types.py
After running, re-process the Nominal Roll to remap employees.

Adds:
  - Political
  - Secondment
  - Secondment on National Interest
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from sqlalchemy.dialects.postgresql import insert as pg_insert
from owl.load.database import get_session
from owl.load.models import EmploymentType
from owl.logger import get_logger

log = get_logger(__name__)

MISSING_TYPES = [
    "Political",
    "Secondment",
    "Secondment on National Interest",
]


def migrate() -> None:
    with get_session() as session:
        table = EmploymentType.__table__
        for name in MISSING_TYPES:
            stmt = (
                pg_insert(table)
                .values(emp_type_name=name)
                .on_conflict_do_nothing()
            )
            session.execute(stmt)

        session.commit()
        log.info(f"Ensured {len(MISSING_TYPES)} employment types exist.")
        for name in MISSING_TYPES:
            log.info(f"  - {name}")

    log.info("Migration complete. Re-process Nominal Roll to remap employees.")


if __name__ == "__main__":
    migrate()
