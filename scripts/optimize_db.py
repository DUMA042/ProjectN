import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import psycopg2
from sqlalchemy.engine import make_url

from owl.config import settings


def _pg_params() -> dict:
    """Connection parameters from DATABASE_URL — never hardcoded."""
    url = make_url(settings.get_database_url())
    return {
        "dbname": url.database,
        "user": url.username,
        "password": url.password,
        "host": url.host,
        "port": url.port,
    }

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
    params = _pg_params()
    try:
        print(f"Connecting to database '{params['dbname']}' on port {params['port']}...")
        conn = psycopg2.connect(**params)
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
