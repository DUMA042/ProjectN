import sys
import psycopg2

DB_NAME = "flowdb"
DB_USER = "postgres"
DB_PASSWORD = "1234"
DB_HOST = "localhost"
DB_PORT = "5433"

ADDITIONAL_DDL = """
CREATE TABLE IF NOT EXISTS leave_types (
    leave_type_id SERIAL PRIMARY KEY,
    leave_type_name VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS employee_leaves (
    leave_id SERIAL PRIMARY KEY,
    id_no VARCHAR(50) REFERENCES employees(id_no) ON DELETE CASCADE,
    leave_type_id INTEGER REFERENCES leave_types(leave_type_id) ON DELETE RESTRICT,
    start_date DATE NOT NULL,
    end_date DATE
);

CREATE TABLE IF NOT EXISTS employee_card_swipes (
    swipe_id SERIAL PRIMARY KEY,
    id_no VARCHAR(50) REFERENCES employees(id_no) ON DELETE CASCADE,
    location_id INTEGER REFERENCES locations(location_id) ON DELETE SET NULL,
    swipe_time TIMESTAMP NOT NULL
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_emp_leave_id ON employee_leaves(id_no);
CREATE INDEX IF NOT EXISTS idx_emp_swipe_id ON employee_card_swipes(id_no);
CREATE INDEX IF NOT EXISTS idx_emp_swipe_time ON employee_card_swipes(swipe_time);
"""

def setup_additional_schema():
    try:
        print("Connecting to flowdb...")
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
        conn.autocommit = True
        cur = conn.cursor()
        
        print("Executing DDL for Leave and Card Additions...")
        cur.execute(ADDITIONAL_DDL)
        print("Schema Additions Created Successfully.")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Failed to create schema: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    setup_additional_schema()
