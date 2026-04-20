import psycopg2
import sys

def list_indexes():
    try:
        conn = psycopg2.connect("postgresql://postgres:1234@localhost:5433/flowdb")
        cur = conn.cursor()
        cur.execute("""
            SELECT tablename, indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname;
        """)
        
        indexes = cur.fetchall()
        if not indexes:
            print("No indexes found in the public schema.")
            return

        current_table = None
        for tablename, indexname, indexdef in indexes:
            if tablename != current_table:
                print(f"\n--- Table: {tablename} ---")
                current_table = tablename
            print(f"Index: {indexname}")
            print(f"  {indexdef}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)

if __name__ == "__main__":
    list_indexes()
