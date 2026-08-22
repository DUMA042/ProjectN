"""Temporary script — clear all leave data before re-uploading.

Deletes all rows from leave_records and leave_applications, resets the
serial sequences so new data starts from ID 1, and clears any Leave-related
file_ingestion_meta records. Leaves employees, leave_types, card swipes,
trainings, and all other tables untouched.

Usage
-----
    python scratch/clear_leave_data.py
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from sqlalchemy import text
from owl.load.database import get_session


def main() -> None:
    with get_session() as s:
        # 1. Delete child records first
        recs = s.execute(text("DELETE FROM leave_records")).rowcount

        # 2. Delete parent applications
        apps = s.execute(text("DELETE FROM leave_applications")).rowcount

        # 3. Reset serial sequences so new data starts from 1
        s.execute(text("ALTER SEQUENCE leave_records_record_id_seq RESTART WITH 1"))
        s.execute(text("ALTER SEQUENCE leave_applications_application_id_seq RESTART WITH 1"))

        # 4. Clear Leave-related ingestion history (old files can be re-uploaded)
        meta = s.execute(text("DELETE FROM file_ingestion_meta WHERE report_type = 'Leave'")).rowcount

        s.commit()

        # 5. Verify
        lr = s.execute(text("SELECT COUNT(*) FROM leave_records")).scalar()
        la = s.execute(text("SELECT COUNT(*) FROM leave_applications")).scalar()
        lt = s.execute(text("SELECT COUNT(*) FROM leave_types")).scalar()
        emp = s.execute(text("SELECT COUNT(*) FROM employees")).scalar()

        print("=" * 50)
        print("LEAVE DATA CLEARED")
        print("=" * 50)
        print(f"Deleted leave_records:      {recs}")
        print(f"Deleted leave_applications: {apps}")
        print(f"Deleted Leave ingestion:    {meta}")
        print("-" * 50)
        print(f"Remaining leave_records:    {lr}")
        print(f"Remaining leave_applications:{la}")
        print(f"leave_types (untouched):    {lt}")
        print(f"employees (untouched):      {emp}")


if __name__ == "__main__":
    main()
