import sys
import psycopg2

# Connection Settings
DB_NAME = "flowdb"
DB_USER = "postgres"
DB_PASSWORD = "1234"
DB_HOST = "localhost"
DB_PORT = "5433"

OPTIMIZATION_DDL = """
-- Performance Indexes for History and Swiping tables

-- Index 1: Optimize searches for employees at specific locations over time
CREATE INDEX IF NOT EXISTS idx_loc_hist_date 
ON employee_location_history (location_id, start_date, end_date);

-- Index 2: Optimize searches for department history by date range
CREATE INDEX IF NOT EXISTS idx_dept_hist_date 
ON employee_department_history (start_date, end_date);

-- Index 3: Optimize searches for grade level history by date range
CREATE INDEX IF NOT EXISTS idx_gl_hist_date 
ON employee_gl_history (start_date, end_date);

-- Index 4: Optimize per-employee attendance/swipe queries
CREATE INDEX IF NOT EXISTS idx_swipe_date 
ON employee_card_swipes (id_no, swipe_time);
"""

def apply_optimizations():
    try:
        print(f"Connecting to {DB_NAME} on port {DB_PORT}...")
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
        conn.autocommit = True
        cur = conn.cursor()
        
        print("Applying composite indexes for performance...")
        cur.execute(OPTIMIZATION_DDL)
        print("Indexes created successfully.")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Failed to apply optimizations: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    apply_optimizations()
