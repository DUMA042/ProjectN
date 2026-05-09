import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

def analyze_units():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        print("--- Unit Analysis ---")
        
        # 1. Total employees with a unit
        res = conn.execute(text("SELECT count(*) FROM employees WHERE unit_id IS NOT NULL;"))
        print(f"Employees with a unit in main table: {res.scalar()}")
        
        # 2. Total active unit history records
        res = conn.execute(text("SELECT count(*) FROM employee_unit_history WHERE end_date IS NULL;"))
        print(f"Active unit history records: {res.scalar()}")
        
        # 3. Mismatches (Unit in main table differs from active history, or history missing)
        res = conn.execute(text("""
            SELECT count(*) 
            FROM employees e
            LEFT JOIN employee_unit_history h 
                ON e.id_no = h.id_no AND h.end_date IS NULL
            WHERE e.unit_id IS NOT NULL 
              AND (h.unit_id IS NULL OR e.unit_id != h.unit_id);
        """))
        print(f"Employees with unit but missing/mismatched active history: {res.scalar()}")
        
        # 4. Reverse Mismatch (History exists but missing in main table)
        res = conn.execute(text("""
            SELECT count(*) 
            FROM employee_unit_history h
            LEFT JOIN employees e 
                ON e.id_no = h.id_no
            WHERE h.end_date IS NULL 
              AND (e.unit_id IS NULL OR e.unit_id != h.unit_id);
        """))
        print(f"Active history exists but missing/mismatched in main table: {res.scalar()}")

if __name__ == "__main__":
    analyze_units()
