import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

def migrate():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            print("1. Adding columns to 'employees'...")
            conn.execute(text("ALTER TABLE employees ADD COLUMN IF NOT EXISTS department_id INTEGER REFERENCES departments(department_id);"))
            conn.execute(text("ALTER TABLE employees ADD COLUMN IF NOT EXISTS gl_id INTEGER REFERENCES grade_levels(gl_id);"))
            
            print("2. Creating new history tables...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS employee_unit_history (
                    history_id SERIAL PRIMARY KEY,
                    id_no VARCHAR(64) REFERENCES employees(id_no),
                    unit_id INTEGER REFERENCES units(unit_id),
                    start_date DATE NOT NULL,
                    end_date DATE
                );
                CREATE TABLE IF NOT EXISTS employee_rank_history (
                    history_id SERIAL PRIMARY KEY,
                    id_no VARCHAR(64) REFERENCES employees(id_no),
                    rank_id INTEGER REFERENCES ranks(rank_id),
                    start_date DATE NOT NULL,
                    end_date DATE
                );
            """))
            
            print("3. Backfilling 'employees' table from history...")
            # Backfill Dept
            conn.execute(text("""
                UPDATE employees e
                SET department_id = (
                    SELECT department_id FROM employee_department_history h 
                    WHERE h.id_no = e.id_no AND h.end_date IS NULL 
                    ORDER BY h.start_date DESC LIMIT 1
                )
                WHERE e.department_id IS NULL;
            """))
            # Backfill GL
            conn.execute(text("""
                UPDATE employees e
                SET gl_id = (
                    SELECT gl_id FROM employee_gl_history h 
                    WHERE h.id_no = e.id_no AND h.end_date IS NULL 
                    ORDER BY h.start_date DESC LIMIT 1
                )
                WHERE e.gl_id IS NULL;
            """))
            
            print("4. Updating Trigger Logic (Universal History Logger)...")
            # Create a reusable function for history logging
            conn.execute(text("""
                CREATE OR REPLACE FUNCTION log_combined_history()
                RETURNS trigger AS $func$
                BEGIN
                    -- 1. Unit History
                    IF (TG_OP = 'INSERT') OR (OLD.unit_id IS DISTINCT FROM NEW.unit_id) THEN
                        UPDATE employee_unit_history SET end_date = CURRENT_DATE WHERE id_no = NEW.id_no AND end_date IS NULL;
                        INSERT INTO employee_unit_history(id_no, unit_id, start_date) VALUES (NEW.id_no, NEW.unit_id, CURRENT_DATE);
                    END IF;
                    
                    -- 2. Rank History
                    IF (TG_OP = 'INSERT') OR (OLD.rank_id IS DISTINCT FROM NEW.rank_id) THEN
                        UPDATE employee_rank_history SET end_date = CURRENT_DATE WHERE id_no = NEW.id_no AND end_date IS NULL;
                        INSERT INTO employee_rank_history(id_no, rank_id, start_date) VALUES (NEW.id_no, NEW.rank_id, CURRENT_DATE);
                    END IF;
                    
                    -- 3. Location History
                    IF (TG_OP = 'INSERT') OR (OLD.location_id IS DISTINCT FROM NEW.location_id) THEN
                        UPDATE employee_location_history SET end_date = CURRENT_DATE WHERE id_no = NEW.id_no AND end_date IS NULL;
                        INSERT INTO employee_location_history(id_no, location_id, start_date) VALUES (NEW.id_no, NEW.location_id, CURRENT_DATE);
                    END IF;
                    
                    -- 4. Department History
                    IF (TG_OP = 'INSERT') OR (OLD.department_id IS DISTINCT FROM NEW.department_id) THEN
                        UPDATE employee_department_history SET end_date = CURRENT_DATE WHERE id_no = NEW.id_no AND end_date IS NULL;
                        INSERT INTO employee_department_history(id_no, department_id, start_date) VALUES (NEW.id_no, NEW.department_id, CURRENT_DATE);
                    END IF;
                    
                    -- 5. GL History
                    IF (TG_OP = 'INSERT') OR (OLD.gl_id IS DISTINCT FROM NEW.gl_id) THEN
                        UPDATE employee_gl_history SET end_date = CURRENT_DATE WHERE id_no = NEW.id_no AND end_date IS NULL;
                        INSERT INTO employee_gl_history(id_no, gl_id, start_date) VALUES (NEW.id_no, NEW.gl_id, CURRENT_DATE);
                    END IF;
                    
                    RETURN NEW;
                END;
                $func$ LANGUAGE plpgsql;
            """))
            
            # Re-create the trigger on employees
            conn.execute(text("DROP TRIGGER IF EXISTS trg_log_employee_history ON employees;"))
            conn.execute(text("""
                CREATE TRIGGER trg_log_employee_history
                AFTER INSERT OR UPDATE ON employees
                FOR EACH ROW EXECUTE FUNCTION log_combined_history();
            """))
            
            # Remove obsolete function
            conn.execute(text("DROP FUNCTION IF EXISTS log_employee_history();"))
            
            trans.commit()
            print("\nMIGRATION SUCCESSFUL: History system automated.")
            
        except Exception as e:
            trans.rollback()
            print(f"\nMIGRATION FAILED: {e}")
            raise

if __name__ == "__main__":
    migrate()
