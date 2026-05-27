from owl.load.database import get_session
from sqlalchemy import text

def alter_leave_records():
    queries = [
        "ALTER TABLE leave_records ADD COLUMN IF NOT EXISTS planned_start_date DATE;",
        "ALTER TABLE leave_records ADD COLUMN IF NOT EXISTS planned_start_date_raw VARCHAR(255);",
        "ALTER TABLE leave_records ADD COLUMN IF NOT EXISTS planned_end_date DATE;",
        "ALTER TABLE leave_records ADD COLUMN IF NOT EXISTS planned_end_date_raw VARCHAR(255);"
    ]
    
    try:
        with get_session() as session:
            for query in queries:
                session.execute(text(query))
            session.commit()
            print("Successfully added planned date columns to leave_records.")
    except Exception as e:
        print(f"Error altering database: {e}")

if __name__ == "__main__":
    alter_leave_records()
