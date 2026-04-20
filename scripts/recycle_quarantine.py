"""
scripts/recycle_quarantine.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Utility to move files from Quarantine back to Inbox for reprocessing.
Removes timestamp suffixes added during failed ingestion attempts.
"""

import os
import shutil
import re
from pathlib import Path

# Project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
QUARANTINE_DIR = _PROJECT_ROOT / "nest" / "Quarantine"
INBOX_DIR = _PROJECT_ROOT / "inbox"

def recycle_quarantine():
    if not QUARANTINE_DIR.exists():
        print(f"Quarantine directory not found: {QUARANTINE_DIR}")
        return

    INBOX_DIR.mkdir(exist_ok=True, parents=True)
    
    # Pattern to match timestamp suffix: filename.xlsx_123456789.xlsx
    timestamp_pattern = re.compile(r"(.+?\.xlsx)_\d+\.xlsx$")
    
    files = list(QUARANTINE_DIR.glob("*.xlsx"))
    print(f"Found {len(files)} files in Quarantine.")

    for f_path in files:
        name = f_path.name
        match = timestamp_pattern.match(name)
        
        if match:
            # Reconstruct original name
            new_name = match.group(1)
        else:
            new_name = name
            
        dest_path = INBOX_DIR / new_name
        
        # Avoid collisions in inbox
        if dest_path.exists():
            dest_path = INBOX_DIR / f"recovered_{name}"
            
        print(f"Recycling: {name} -> {dest_path.name}")
        shutil.move(str(f_path), str(dest_path))

    print("Recycle complete.")

if __name__ == "__main__":
    recycle_quarantine()
