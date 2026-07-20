"""
scripts/add_training_title_column.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
One-time migration — adds 'title' column to training tables.
Run once:  python scripts/add_training_title_column.py
"""

import sys
from pathlib import Path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from owl.load.database import get_engine
from owl.logger import get_logger
from sqlalchemy import text

log = get_logger(__name__)

SQL_UP = [
    "ALTER TABLE public.employee_trainings ADD COLUMN IF NOT EXISTS title TEXT",
    "ALTER TABLE public.quarantine_trainings ADD COLUMN IF NOT EXISTS title TEXT",
]


def migrate() -> None:
    engine = get_engine()
    with engine.begin() as conn:
        for stmt in SQL_UP:
            conn.execute(text(stmt))
    log.info("Added 'title' column to employee_trainings and quarantine_trainings.")


if __name__ == "__main__":
    migrate()
