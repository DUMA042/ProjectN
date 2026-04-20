"""
scripts/scratch/alter_quarantine_schema.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Alters the schema of quarantine_card_swipes to accommodate the newly requested logic 
without dropping previous records.
"""

import sys
from pathlib import Path
from sqlalchemy import text

# Add the project root to sys.path so we can import from owl
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from owl.load.database import get_engine
from owl.logger import get_logger

log = get_logger(__name__)

def main():
    engine = get_engine()
    
    with engine.begin() as conn:
        # Step 1: Drop the NOT NULL constraint on id_no safely
        log.info("Altering quarantine_card_swipes: dropping NOT NULL from id_no...")
        conn.execute(text("ALTER TABLE quarantine_card_swipes ALTER COLUMN id_no DROP NOT NULL;"))
        
        # Step 2: Add employee_name column safely
        log.info("Altering quarantine_card_swipes: adding employee_name column...")
        conn.execute(text("ALTER TABLE quarantine_card_swipes ADD COLUMN IF NOT EXISTS employee_name VARCHAR(255);"))
        
    log.info("Database schema update completed successfully.")

if __name__ == "__main__":
    main()
