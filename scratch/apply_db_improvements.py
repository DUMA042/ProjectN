import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

def apply_improvements():
    load_dotenv()
    db_url = os.getenv('DATABASE_URL')
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            print("1. Standardizing id_no to VARCHAR(64) globally...")
            # To alter a PK referenced by FKs, PG requires dropping the FKs, or altering them simultaneously. 
            # The safest approach is to explicitly DROP the FKs, alter the types, and ADD the FKs back.
            
            # Drop foreign keys pointing to employees.id_no
            fks = [
                ("employee_location_history", "employee_location_history_id_no_fkey"),
                ("employee_department_history", "employee_department_history_id_no_fkey"),
                ("employee_gl_history", "employee_gl_history_id_no_fkey"),
                ("employee_trainings", "employee_trainings_id_no_fkey"),
                ("employee_unit_history", "employee_unit_history_id_no_fkey"),
                ("employee_rank_history", "employee_rank_history_id_no_fkey"),
                ("employee_leaves", "employee_leaves_id_no_fkey"),
                ("employee_card_swipes", "employee_card_swipes_id_no_fkey")
            ]
            
            for table, fk_name in fks:
                conn.execute(text(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {fk_name};"))
            
            # Alter columns
            tables_with_id_no = [
                "employees", 
                "employee_location_history", 
                "employee_department_history", 
                "employee_gl_history", 
                "employee_trainings", 
                "employee_leaves", 
                "employee_card_swipes"
            ]
            for t in tables_with_id_no:
                conn.execute(text(f"ALTER TABLE {t} ALTER COLUMN id_no TYPE VARCHAR(64);"))
            
            # Re-add foreign keys
            for table, fk_name in fks:
                conn.execute(text(f"ALTER TABLE {table} ADD CONSTRAINT {fk_name} FOREIGN KEY (id_no) REFERENCES employees(id_no);"))

            print("2. Fixing Timezone on employee_card_swipes...")
            conn.execute(text("ALTER TABLE employee_card_swipes ALTER COLUMN swipe_time TYPE TIMESTAMP WITH TIME ZONE;"))

            print("3. Adding Performance Indexes for SCD Type 4...")
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_emp_dept_hist_active ON employee_department_history (id_no) WHERE end_date IS NULL;"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_emp_loc_hist_active ON employee_location_history (id_no) WHERE end_date IS NULL;"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_emp_gl_hist_active ON employee_gl_history (id_no) WHERE end_date IS NULL;"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_emp_unit_hist_active ON employee_unit_history (id_no) WHERE end_date IS NULL;"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_emp_rank_hist_active ON employee_rank_history (id_no) WHERE end_date IS NULL;"))

            trans.commit()
            print("Improvements successfully applied!")
            
        except Exception as e:
            trans.rollback()
            print(f"FAILED to apply improvements: {e}")

if __name__ == "__main__":
    apply_improvements()
