"""
scripts/forget_ingestions.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Utility script to remove the tracking history of recently processed files.

If you drop a file into the inbox and the pipeline quarantines it with the message 
"Duplicate file content", it is because the system remembers the checksum of that file.
Running this script allows the system to "forget" that it processed the file, so you 
can safely drop the exact same file into the inbox and process it again.

Usage
-----
    # Remove the single most recently processed file
    python scripts/forget_ingestions.py

    # Remove the last 3 processed files
    python scripts/forget_ingestions.py -c 3
    python scripts/forget_ingestions.py --count 3
"""

import sys
import argparse
from pathlib import Path
from sqlalchemy import select

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from owl.load.database import get_session
from owl.load.models import FileIngestionMeta
from owl.logger import get_logger

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Forget recently processed files to allow re-processing.")
    parser.add_argument(
        "-c", "--count",
        type=int,
        default=1,
        help="Number of recent file records to remove (default: 1)"
    )
    args = parser.parse_args()

    if args.count <= 0:
        log.error("Count must be greater than 0.")
        return

    log.info(f"Looking for the last {args.count} ingestion record(s)...")

    with get_session() as session:
        # Fetch the most recent N records based on creation time
        stmt = select(FileIngestionMeta).order_by(FileIngestionMeta.created_at.desc()).limit(args.count)
        recent_records = session.execute(stmt).scalars().all()

        if not recent_records:
            log.info("No ingestion records found in the database.")
            return

        log.info(f"Found {len(recent_records)} record(s) to remove:")
        
        for record in recent_records:
            log.info(f"  - Forgetting: '{record.original_filename}' (Status: {record.status}, Processed: {record.created_at.strftime('%Y-%m-%d %H:%M:%S')})")
            session.delete(record)
            
        session.commit()
        
    log.info("\nSuccess! The system has forgotten these files.")
    log.info("You can now safely drop these exact files back into the inbox and process them without getting a 'Duplicate file content' quarantine.")

if __name__ == "__main__":
    main()
