import sys
from pathlib import Path
from sqlalchemy import text

# Add project root to path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from owl.load.database import get_session
from owl.logger import get_logger

log = get_logger(__name__)

def run_migration():
    log.info("Starting safe historical tracking migration...")

    alter_sql = """
    -- 1. Safely add location_id column to existing employees table
    ALTER TABLE employees ADD COLUMN IF NOT EXISTS location_id INTEGER;
    
    DO $$ 
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE constraint_name = 'fk_employees_location' AND table_name = 'employees'
        ) THEN
            ALTER TABLE employees 
            ADD CONSTRAINT fk_employees_location 
            FOREIGN KEY (location_id) REFERENCES locations(location_id);
        END IF;
    END $$;

    -- 2. Create the standalone employee_history table
    CREATE TABLE IF NOT EXISTS employee_history (
        history_id SERIAL PRIMARY KEY,
        id_no VARCHAR(64) NOT NULL REFERENCES employees(id_no),
        unit_id INTEGER REFERENCES units(unit_id),
        rank_id INTEGER REFERENCES ranks(rank_id),
        location_id INTEGER REFERENCES locations(location_id),
        effective_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS ix_employee_history_id_no ON employee_history(id_no);

    -- 3. Create the Database Trigger Function
    CREATE OR REPLACE FUNCTION log_employee_history()
    RETURNS TRIGGER AS $$
    BEGIN
        -- Only insert if there was an actual change in the key tracking metrics
        IF (OLD.unit_id IS DISTINCT FROM NEW.unit_id) OR 
           (OLD.rank_id IS DISTINCT FROM NEW.rank_id) OR
           (OLD.location_id IS DISTINCT FROM NEW.location_id) THEN
           
           INSERT INTO employee_history(id_no, unit_id, rank_id, location_id, effective_date)
           VALUES (OLD.id_no, OLD.unit_id, OLD.rank_id, OLD.location_id, CURRENT_TIMESTAMP);
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    -- 4. Attach the Trigger
    DROP TRIGGER IF EXISTS trg_log_employee_history ON employees;
    CREATE TRIGGER trg_log_employee_history
    AFTER UPDATE ON employees
    FOR EACH ROW
    EXECUTE FUNCTION log_employee_history();
    """

    try:
        with get_session() as session:
            session.execute(text(alter_sql))
            session.commit()
            log.info("Migration successful! Employee History table and Triggers gracefully installed.")
    except Exception as e:
        log.error(f"Migration failed: {e}")

if __name__ == "__main__":
    run_migration()
