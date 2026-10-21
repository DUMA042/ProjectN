# HISTORICAL SETUP SCRIPT — DO NOT RE-RUN AGAINST PRODUCTION.
# Use scripts/migrate_nominal_schema.py for schema migrations.

import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys

# No credentials in code: supply FLOW_DB_PASSWORD (and optionally the other
# FLOW_DB_* variables) in the environment when running this historical script.
DB_NAME = os.environ.get("FLOW_DB_NAME", "flowdb")
DB_USER = os.environ.get("FLOW_DB_USER", "postgres")
DB_PASSWORD = os.environ.get("FLOW_DB_PASSWORD", "")
DB_HOST = os.environ.get("FLOW_DB_HOST", "localhost")
DB_PORT = os.environ.get("FLOW_DB_PORT", "5433")

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
    if not DB_PASSWORD:
        print(
            "FLOW_DB_PASSWORD is not set. Export it (and FLOW_DB_* overrides if "
            "needed) before running this historical setup script.",
            file=sys.stderr,
        )
        sys.exit(1)
    create_db_if_missing()
    run_ddl()

    print(
        "\nDatabase ready. Create your .env from .env.example and set "
        "DATABASE_URL (this script no longer writes credentials to disk)."
    )
