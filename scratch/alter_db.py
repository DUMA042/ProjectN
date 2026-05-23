import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from owl.load.database import get_engine
from sqlalchemy import text

def alter_db():
    engine = get_engine()
    with engine.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE leave_records ADD COLUMN start_date_raw VARCHAR(255);"))
        except Exception as e:
            print("start_date_raw might already exist:", e)
            
        try:
            conn.execute(text("ALTER TABLE leave_records ADD COLUMN end_date_raw VARCHAR(255);"))
        except Exception as e:
            print("end_date_raw might already exist:", e)
            
        try:
            # We also need to drop the NOT NULL constraint on start_date
            conn.execute(text("ALTER TABLE leave_records ALTER COLUMN start_date DROP NOT NULL;"))
        except Exception as e:
            print("start_date might already be optional:", e)

if __name__ == "__main__":
    alter_db()
    print("DB Altered.")
