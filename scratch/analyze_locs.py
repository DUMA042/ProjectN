import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

def analyze_locations():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        print("--- Location Analysis ---")
        
        # 1. Total employees with a location
        res = conn.execute(text("SELECT count(*) FROM employees WHERE location_id IS NOT NULL;"))
        print(f"Employees with a location in main table: {res.scalar()}")
        
        # 2. Total active location history records
        res = conn.execute(text("SELECT count(*) FROM employee_location_history WHERE end_date IS NULL;"))
        print(f"Active location history records: {res.scalar()}")
        
        # 3. Mismatches (Location in main table differs from active history, or history missing)
        res = conn.execute(text("""
            SELECT count(*) 
            FROM employees e
            LEFT JOIN employee_location_history h 
                ON e.id_no = h.id_no AND h.end_date IS NULL
            WHERE e.location_id IS NOT NULL 
              AND (h.location_id IS NULL OR e.location_id != h.location_id);
        """))
        print(f"Employees with location but missing/mismatched active history: {res.scalar()}")

if __name__ == "__main__":
    analyze_locations()
