import os
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from owl.load.models import Base, Employee, Department, EmployeeDepartmentHistory

def sanity_check():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    engine = create_engine(db_url)
    
    print("Checking model-to-table mapping...")
    for table_name in Base.metadata.tables:
        print(f"  - Model found for table: {table_name}")

    with Session(engine) as session:
        # Try a simple query on a few tables
        try:
            emp_count = session.query(Employee).limit(1).count()
            print(f"Connection check: 'employees' table is reachable (count: {emp_count})")
            
            dept_count = session.query(Department).limit(1).count()
            print(f"Connection check: 'departments' table is reachable (count: {dept_count})")
            
            hist_count = session.query(EmployeeDepartmentHistory).limit(1).count()
            print(f"Connection check: 'employee_department_history' table is reachable (count: {hist_count})")
            
            print("\nSUCCESS: All critical models are aligned with the database.")
        except Exception as e:
            print(f"\nFAILURE: Alignment error: {e}")

if __name__ == "__main__":
    sanity_check()
