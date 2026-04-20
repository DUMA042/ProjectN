"""
scripts/migrate_card_swipes.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Direct migration script to process all Excel files in the card_Swiping_Folder.
"""

from __future__ import annotations

import sys
from pathlib import Path
from sqlalchemy import select

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from owl.config import settings
from owl.logger import get_logger
from owl.load.database import get_session
from owl.load.models import Employee
from owl.pipeline import Pipeline
from owl.transform.sheets.card_swipe import CardSwipeNormalizer

log = get_logger(__name__)

def get_name_to_id_map() -> dict[str, str]:
    """Fetch active employee names and IDs from the database to map card swipes."""
    name_to_id = {}
    try:
        with get_session() as session:
            # Query both full_name and id_no
            res = session.execute(select(Employee.full_name, Employee.id_no)).all()
            for full_name, id_no in res:
                if full_name:
                    cleaned_name = full_name.lower().strip()
                    name_to_id[cleaned_name] = id_no
            log.info(f"Loaded {len(name_to_id)} valid employee name mappings from the database.")
    except Exception as exc:
        log.error(f"Failed to fetch employee names: {exc}")
    
    return name_to_id

def main() -> None:
    target_dir = settings.nest_dir / "card_Swiping_Folder"
    
    if not target_dir.exists():
        log.error(f"Target directory does not exist: {target_dir}")
        return

    excel_files = list(target_dir.glob("*.xlsx"))
    if not excel_files:
        log.warning(f"No '.xlsx' files found in {target_dir}.")
        return

    log.info(f"Found {len(excel_files)} files to process in {target_dir.name}.")
    
    # Pre-fetch name to id map
    name_to_id = get_name_to_id_map()
    if not name_to_id:
        log.warning("No valid employee names found in database. All records will be quarantined.")

    success_count = 0
    failure_count = 0
    unmapped_names = set()

    for file_path in excel_files:
        try:
            log.info(f"=== Starting pipeline for: {file_path.name} ===")
            
            pipeline = Pipeline(
                source_file=file_path,
                normalizer_class=CardSwipeNormalizer,
                sheet_names=None,  # Process all sheets
                header_row=1,      # Default header row as per profile
                context={"name_to_id": name_to_id, "unmapped_names": unmapped_names}
            )
            
            result = pipeline.run()
            status = result.get("status")
            
            if status == "completed":
                load_results = result.get("load_results", {})
                for table, counts in load_results.items():
                    log.info(
                        f"  -> {table}: "
                        f"{counts.get('success', 0)} loaded, "
                        f"{counts.get('failed', 0)} failed"
                    )
                success_count += 1
            else:
                log.error(f"Pipeline failed for {file_path.name}: {result.get('error')}")
                failure_count += 1
                
        except Exception as exc:
            log.exception(f"Unexpected error processing {file_path.name}: {exc}")
            failure_count += 1

    log.info("=== Migration Summary ===")
    log.info(f"Successfully processed: {success_count} file(s)")
    log.info(f"Failed to process: {failure_count} file(s)")
    
    # Print out all names that failed to map
    if unmapped_names:
        log.warning("\n" + "="*50)
        log.warning(f"UNMAPPED NAMES ({len(unmapped_names)} Total Sent to Quarantine)")
        log.warning("="*50)
        for name in sorted(unmapped_names):
            print(f"- {name}")
        log.warning("="*50 + "\n")

if __name__ == "__main__":
    main()
