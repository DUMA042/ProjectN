import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

def seed_history_baselines():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            print("Seeding baseline history for existing employees...")
            
            # 1. Seed Units
            res_unit = conn.execute(text("""
                INSERT INTO employee_unit_history (id_no, unit_id, start_date)
                SELECT id_no, unit_id, CURRENT_DATE 
                FROM employees e
                WHERE NOT EXISTS (
                    SELECT 1 FROM employee_unit_history h WHERE h.id_no = e.id_no
                ) AND e.unit_id IS NOT NULL;
            """))
            
            # 2. Seed Ranks
            res_rank = conn.execute(text("""
                INSERT INTO employee_rank_history (id_no, rank_id, start_date)
                SELECT id_no, rank_id, CURRENT_DATE 
                FROM employees e
                WHERE NOT EXISTS (
                    SELECT 1 FROM employee_rank_history h WHERE h.id_no = e.id_no
                ) AND e.rank_id IS NOT NULL;
            """))
            
            # 3. Seed Departments (for any missed in backfill)
            res_dept = conn.execute(text("""
                INSERT INTO employee_department_history (id_no, department_id, start_date)
                SELECT id_no, department_id, CURRENT_DATE 
                FROM employees e
                WHERE NOT EXISTS (
                    SELECT 1 FROM employee_department_history h WHERE h.id_no = e.id_no
                ) AND e.department_id IS NOT NULL;
            """))

            # 4. Seed GL (for any missed)
            res_gl = conn.execute(text("""
                INSERT INTO employee_gl_history (id_no, gl_id, start_date)
                SELECT id_no, gl_id, CURRENT_DATE 
                FROM employees e
                WHERE NOT EXISTS (
                    SELECT 1 FROM employee_gl_history h WHERE h.id_no = e.id_no
                ) AND e.gl_id IS NOT NULL;
            """))

            trans.commit()
            print(f"COMPLETE: Created baseline records.")
            print(f" - Units: {res_unit.rowcount}")
            print(f" - Ranks: {res_rank.rowcount}")
            print(f" - Departments: {res_dept.rowcount}")
            print(f" - Grade Levels: {res_gl.rowcount}")
            
        except Exception as e:
            trans.rollback()
            print(f"ERROR: Seeding failed: {e}")
            raise

if __name__ == "__main__":
    seed_history_baselines()
