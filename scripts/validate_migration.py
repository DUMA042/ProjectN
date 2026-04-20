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
        
        print("\n--- Test 1: Check Total Record Count ---")
        df1 = pd.read_sql("SELECT COUNT(*) FROM employees;", conn)
        print(df1)
        
        print("\n--- Test 2: Verify S/N Generation (Top 5) ---")
        df2 = pd.read_sql("SELECT serial_no, id_no, full_name FROM employees ORDER BY serial_no LIMIT 5;", conn)
        print(df2)
        
        print("\n--- Test 3: Relational Join Test (Sample 5 Active) ---")
        query3 = """
        SELECT 
            e.serial_no AS "S/N",
            e.full_name AS "Name",
            e.sex AS "Sex",
            e.id_no AS "ID No",
            g.gl_name AS "GL",
            r.rank_name AS "Rank",
            d.department_name AS "Department",
            l.location_name AS "Location"
        FROM employees e
        LEFT JOIN employee_gl_history egh ON e.id_no = egh.id_no AND egh.end_date IS NULL
        LEFT JOIN grade_levels g ON egh.gl_id = g.gl_id
        LEFT JOIN employee_department_history edh ON e.id_no = edh.id_no AND edh.end_date IS NULL
        LEFT JOIN departments d ON edh.department_id = d.department_id
        LEFT JOIN employee_location_history elh ON e.id_no = elh.id_no AND elh.end_date IS NULL
        LEFT JOIN locations l ON elh.location_id = l.location_id
        LEFT JOIN ranks r ON e.rank_id = r.rank_id
        LIMIT 5;
        """
        df3 = pd.read_sql(query3, conn)
        print(df3)
        
        print("\n--- Test 4: Verify History Constraints (Should return Empty) ---")
        query4 = """
        SELECT id_no, COUNT(*) 
        FROM employee_location_history 
        WHERE end_date IS NULL 
        GROUP BY id_no 
        HAVING COUNT(*) > 1;
        """
        df4 = pd.read_sql(query4, conn)
        print(df4)
        print(f"Duplicates found: {len(df4)}")
        
        conn.close()
    except Exception as e:
        print(f"Error during validation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
