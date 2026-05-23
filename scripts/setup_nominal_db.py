# HISTORICAL SETUP SCRIPT — DO NOT RE-RUN AGAINST PRODUCTION.
# Use scripts/migrate_nominal_schema.py for schema migrations.

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys

DB_NAME = "flowdb"
DB_USER = "postgres"
DB_PASSWORD = "1234"
DB_HOST = "localhost"
DB_PORT = "5433"

SCHEMA_DDL = """
-- Create Lookup Tables
CREATE TABLE IF NOT EXISTS locations (
    location_id SERIAL PRIMARY KEY,
    location_name VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS departments (
    department_id SERIAL PRIMARY KEY,
    department_name VARCHAR(255) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS grade_levels (
    gl_id SERIAL PRIMARY KEY,
    gl_name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS ranks (
    rank_id SERIAL PRIMARY KEY,
    rank_name VARCHAR(255) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS employment_types (
    emp_type_id SERIAL PRIMARY KEY,
    emp_type_name VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS employee_statuses (
    status_id SERIAL PRIMARY KEY,
    status_name VARCHAR(100) UNIQUE NOT NULL
);

-- Create Main Table (serial_no and unit_id removed)
CREATE TABLE IF NOT EXISTS employees (
    id_no VARCHAR(50) PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    sex VARCHAR(10),
    rank_id INTEGER REFERENCES ranks(rank_id) ON DELETE SET NULL,
    emp_type_id INTEGER REFERENCES employment_types(emp_type_id) ON DELETE SET NULL,
    status_id INTEGER REFERENCES employee_statuses(status_id) ON DELETE SET NULL,
    geographical_zone VARCHAR(100),
    date_of_last_deployment DATE,
    phone_number VARCHAR(30),
    remark TEXT
);

-- Create History Tables
CREATE TABLE IF NOT EXISTS employee_location_history (
    history_id SERIAL PRIMARY KEY,
    id_no VARCHAR(50) REFERENCES employees(id_no) ON DELETE CASCADE,
    location_id INTEGER REFERENCES locations(location_id) ON DELETE RESTRICT,
    start_date DATE NOT NULL,
    end_date DATE
);

CREATE TABLE IF NOT EXISTS employee_department_history (
    history_id SERIAL PRIMARY KEY,
    id_no VARCHAR(50) REFERENCES employees(id_no) ON DELETE CASCADE,
    department_id INTEGER REFERENCES departments(department_id) ON DELETE RESTRICT,
    start_date DATE NOT NULL,
    end_date DATE
);

CREATE TABLE IF NOT EXISTS employee_gl_history (
    history_id SERIAL PRIMARY KEY,
    id_no VARCHAR(50) REFERENCES employees(id_no) ON DELETE CASCADE,
    gl_id INTEGER REFERENCES grade_levels(gl_id) ON DELETE RESTRICT,
    start_date DATE NOT NULL,
    end_date DATE
);

-- Create Indexes
CREATE INDEX IF NOT EXISTS idx_employees_status ON employees(status_id);
CREATE INDEX IF NOT EXISTS idx_loc_hist_id ON employee_location_history(id_no);
CREATE INDEX IF NOT EXISTS idx_dept_hist_id ON employee_department_history(id_no);
CREATE INDEX IF NOT EXISTS idx_gl_hist_id ON employee_gl_history(id_no);
"""

def create_db_if_missing():
    try:
        conn = psycopg2.connect(dbname="postgres", user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        cur.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{DB_NAME}'")
        if not cur.fetchone():
            print(f"Creating database {DB_NAME} on port {DB_PORT}...")
            cur.execute(f"CREATE DATABASE {DB_NAME}")
        else:
            print(f"Database {DB_NAME} already exists on port {DB_PORT}.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error checking/creating database: {e}", file=sys.stderr)
        sys.exit(1)

def run_ddl():
    try:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
        conn.autocommit = True
        cur = conn.cursor()
        print(f"Executing DDL to create tables and schema on {DB_NAME}...")
        cur.execute(SCHEMA_DDL)
        print("Done.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error executing DDL: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    create_db_if_missing()
    run_ddl()
    
    with open(".env", "w") as f:
        f.write(f"DATABASE_URL=postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}\n")
        f.write("NEST_DIR=nest\n")
        f.write("LOG_LEVEL=INFO\n")
        f.write("ENVIRONMENT=development\n")
    print("Created .env with proper config.")
