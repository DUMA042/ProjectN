import psycopg2
import pandas as pd
import sys

# Connection Settings
DB_NAME = "flowdb"
DB_USER = "postgres"
DB_PASSWORD = "1234"
DB_HOST = "localhost"
DB_PORT = "5433"

def run_tests():
    try:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
        
        print("\n--- Test 5: Training Record Cardinality ---")
        df1 = pd.read_sql("SELECT COUNT(*) FROM employee_trainings;", conn)
        print(df1)
        
        print("\n--- Test 6: Invalid Employee Ties ---")
        query2 = """
        SELECT COUNT(*) 
        FROM employee_trainings et
        LEFT JOIN employees e ON et.id_no = e.id_no
        WHERE e.id_no IS NULL;
        """
        df2 = pd.read_sql(query2, conn)
        print("Invalid Records found:", df2.iloc[0, 0])
        
        print("\n--- Test 7: Training Reconstruct Join Test (Sample 5) ---")
        query3 = """
        SELECT 
            e.full_name AS "Name",
            e.id_no AS "ID No",
            v.venue_name AS "Venue",
            c.consultant_name AS "Consultant",
            l.location_name AS "Location",
            et.start_date,
            et.end_date
        FROM employee_trainings et
        JOIN employees e ON et.id_no = e.id_no
        JOIN venues v ON et.venue_id = v.venue_id
        JOIN consultants c ON et.consultant_id = c.consultant_id
        LEFT JOIN locations l ON et.location_id = l.location_id
        LIMIT 5;
        """
        df3 = pd.read_sql(query3, conn)
        print(df3)
        
        conn.close()
    except Exception as e:
        print(f"Error during validation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
