import sys
import psycopg2

DB_NAME = "flowdb"
DB_USER = "postgres"
DB_PASSWORD = "1234"
DB_HOST = "localhost"
DB_PORT = "5433"

TRAINING_DDL = """
CREATE TABLE IF NOT EXISTS venues (
    venue_id SERIAL PRIMARY KEY,
    venue_name VARCHAR(255) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS consultants (
    consultant_id SERIAL PRIMARY KEY,
    consultant_name VARCHAR(255) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS employee_trainings (
    training_id SERIAL PRIMARY KEY,
    id_no VARCHAR(50) REFERENCES employees(id_no) ON DELETE CASCADE,
    venue_id INTEGER REFERENCES venues(venue_id) ON DELETE RESTRICT,
    consultant_id INTEGER REFERENCES consultants(consultant_id) ON DELETE RESTRICT,
    location_id INTEGER REFERENCES locations(location_id) ON DELETE SET NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_emp_train_id ON employee_trainings(id_no);
CREATE INDEX IF NOT EXISTS idx_emp_train_venue ON employee_trainings(venue_id);
"""

def setup_training_schema():
    try:
        print("Connecting to flowdb...")
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
        conn.autocommit = True
        cur = conn.cursor()
        
        print("Executing DDL for Training Additions...")
        cur.execute(TRAINING_DDL)
        print("Schema Additions Created Successfully.")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Failed to create schema: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    setup_training_schema()
