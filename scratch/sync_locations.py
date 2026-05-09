import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

def backfill_locations():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            print("Executing Location Synchronization Data Backfill...")
            
            # Update the main employees table
            result = conn.execute(text("""
                UPDATE employees e
                SET location_id = h.location_id
                FROM employee_location_history h
                WHERE e.id_no = h.id_no 
                  AND h.end_date IS NULL
                  AND e.location_id IS NULL;
            """))
            
            trans.commit()
            print(f"SUCCESS: {result.rowcount} employees successfully synchronized with their active location history.")
            
            # Verify the current state
            count = conn.execute(text("SELECT count(*) FROM employees WHERE location_id IS NOT NULL;")).scalar()
            print(f"Total employees with location now in main table: {count}")

        except Exception as e:
            trans.rollback()
            print(f"ERROR: Sync failed: {e}")

if __name__ == "__main__":
    backfill_locations()
