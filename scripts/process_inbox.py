"""
scripts/process_inbox.py
~~~~~~~~~~~~~~~~~~~~~~~~
CLI runner for processing all files currently in the inbox.

This single command:
1. Scans the 'inbox/' directory.
2. Classifies and moves each file to its respective 'nest/' folder.
3. Automatically triggers the data pipeline to load these files into the database.

Usage
-----
    python scripts/process_inbox.py
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from sqlalchemy import select

from owl.logger import get_logger
from owl.load.database import get_session
from owl.load.models import FileIngestionMeta
from owl.ingest.manager import IngestionManager
from owl.ingest.worker import IngestionWorker

log = get_logger(__name__)

def main() -> None:
    log.info("Starting Inbox processing...")
    
    # 1. Run the Manager to classify and move files from inbox
    manager = IngestionManager()
    manager.run_once()
    
    # 2. Check if there are any pending files to process
    with get_session() as session:
        pending_count = session.execute(
            select(FileIngestionMeta).where(FileIngestionMeta.status == "pending")
        ).scalars().all()
        pending_count = len(pending_count)
        
    if pending_count == 0:
        log.info("No pending files to process. Inbox is empty.")
        return
        
    log.info(f"Found {pending_count} pending file(s). Starting worker...")
    
    # 3. Run the Worker until all pending files are processed
    worker = IngestionWorker()
    while pending_count > 0:
        worker.run_once()
        
        # Re-check count
        with get_session() as session:
            pending_count = session.execute(
                select(FileIngestionMeta).where(FileIngestionMeta.status == "pending")
            ).scalars().all()
            pending_count = len(pending_count)
            
    log.info("All files in the inbox have been successfully processed!")

if __name__ == "__main__":
    main()
