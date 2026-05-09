import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv

# Connection Settings
DB_NAME = "flowdb"
DB_USER = "postgres"
DB_PASSWORD = "1234"
DB_HOST = "localhost"
DB_PORT = "5433"

def upgrade_schema():
    print("Connecting to database...")
    try:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
        cur = conn.cursor()
        
        print("Dropping old employee_leaves table...")
        cur.execute("DROP TABLE IF EXISTS employee_leaves CASCADE;")
        
        print("Creating leave_applications table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS leave_applications (
                application_id SERIAL PRIMARY KEY,
                id_no VARCHAR(64) REFERENCES employees(id_no),
                proposed_leave_date DATE,
                proposed_leave_date_raw VARCHAR(255),
                resumption_date DATE,
                forfeiture VARCHAR(255),
                issuance_date DATE,
                issuance_date_raw VARCHAR(255),
                remark TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        print("Creating leave_records table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS leave_records (
                record_id SERIAL PRIMARY KEY,
                application_id INTEGER REFERENCES leave_applications(application_id) ON DELETE CASCADE,
                id_no VARCHAR(64) REFERENCES employees(id_no),
                leave_type_id INTEGER REFERENCES leave_types(leave_type_id),
                start_date DATE,
                end_date DATE
            );
        """)
        
        print("Seeding new leave types...")
        new_types = [
            'ANNUAL LEAVE', 
            'CASUAL AFTER ANNUAL', 
            'PRE-RETIREMENT LEAVE', 
            'MATERNITY LEAVE', 
            'COMPASSIONATE LEAVE', 
            'PATERNITY LEAVE', 
            'SICK LEAVE', 
            'EXAM LEAVE'
        ]
        for t in new_types:
            cur.execute("INSERT INTO leave_types (leave_type_name) VALUES (%s) ON CONFLICT (leave_type_name) DO NOTHING", (t,))
            
        conn.commit()
        cur.close()
        conn.close()
        print("Schema upgrade successful.")
    except Exception as e:
        print(f"Error upgrading schema: {e}")

if __name__ == "__main__":
    upgrade_schema()
