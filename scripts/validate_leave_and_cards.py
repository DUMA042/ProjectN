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
        
        print("\n--- Test 7: Cardinality Checks ---")
        query1 = """
        SELECT 'Leaves' AS table_name, COUNT(*) FROM employee_leaves
        UNION ALL
        SELECT 'Swipes', COUNT(*) FROM employee_card_swipes;
        """
        df1 = pd.read_sql(query1, conn)
        print(df1)
        
        print("\n--- Test 8: Unmatched/Orphan Checks ---")
        query2 = """
        SELECT 'Orphan Leaves' AS type, COUNT(*) FROM employee_leaves WHERE id_no NOT IN (SELECT id_no FROM employees)
        UNION ALL
        SELECT 'Orphan Swipes', COUNT(*) FROM employee_card_swipes WHERE id_no NOT IN (SELECT id_no FROM employees);
        """
        df2 = pd.read_sql(query2, conn)
        print(df2)
        
        print("\n--- Test 9: Leave Join Test (Sample 5) ---")
        query3 = """
        SELECT 
            e.full_name AS "Name",
            e.id_no AS "ID No",
            lt.leave_type_name AS "Leave Type",
            el.start_date,
            el.end_date
        FROM employee_leaves el
        JOIN employees e ON el.id_no = e.id_no
        JOIN leave_types lt ON el.leave_type_id = lt.leave_type_id
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
