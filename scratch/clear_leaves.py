import psycopg2
from dotenv import load_dotenv
import os

def clear_leave_data():
    # Load environment variables
    load_dotenv()
    
    # Connection parameters
    # Note: Using the parameters found in previous successful connections
    db_params = {
        "dbname": "flowdb",
        "user": "postgres",
        "password": "1234",
        "host": "localhost",
        "port": "5433"
    }

    conn = None
    try:
        print("Connecting to flowdb...")
        conn = psycopg2.connect(**db_params)
        cur = conn.cursor()

        # Disable triggers to avoid FK issues if necessary, 
        # though TRUNCATE with CASCADE is cleaner for these two tables.
        print("Clearing data from leave_records and leave_applications...")
        
        # We truncate leave_records first because it likely has a foreign key to leave_applications
        # CASCADE ensures related records are handled.
        cur.execute("TRUNCATE TABLE leave_records, leave_applications CASCADE;")
        
        conn.commit()
        print("Successfully deleted all data from leave tables.")

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error occurred: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()

if __name__ == "__main__":
    clear_leave_data()
