"""
scripts/reconcile_legacy_data.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Maintenance tool to standardise, route, and audit legacy files already in 'nest/'.

Workflow
--------
1. Discovery: Find all .xlsx files in nest/ (excluding Quarantine).
2. Structural Check: Verify that the file's content matches its location.
3. Routing: Move files to the correct subdirectory if they were misplaced.
4. Naming: Rename files to the strict standard naming convention.
5. Auditing: Register as 'completed' in the database (with checksum for idempotency).
"""

from __future__ import annotations

import sys
import shutil
import time
import os
import gc
from pathlib import Path



# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from owl.config import settings
from owl.extract.classifier import classify_file, ROUTING_MAP, ReportType, StructuralClassifier

from owl.extract.excel_reader import ExcelReader
from owl.load.database import get_session
from owl.load.models import FileIngestionMeta
from owl.logger import get_logger
from owl.transform.cleaner import normalise_column_names
from owl.ingest.manager import IngestionManager

log = get_logger(__name__)

NEST_DIR = settings.nest_dir
QUARANTINE_DIR = NEST_DIR / "Quarantine"


class ReconReport:
    """Tracks the results of the reconciliation process."""
    def __init__(self):
        self.total_scanned = 0
        self.standardised = 0
        self.standardised_correctly = 0
        self.routed = 0
        self.quarantined = 0
        self.duplicates_removed = 0
        self.logs = []

    def print_summary(self):
        log.info("=== RECONCILIATION SUMMARY ===")
        log.info(f"Files Scanned:    {self.total_scanned}")
        log.info(f"Fixed/Standardised: {self.standardised}")
        log.info(f"Protected (OK):    {self.standardised_correctly}")
        log.info(f"Routed/Moved:     {self.routed}")
        log.info(f"Quarantined:      {self.quarantined}")
        log.info(f"Duplicates:       {self.duplicates_removed}")
        log.info("==============================")



def reconcile_legacy_data() -> None:
    """Orchestrate the legacy data reconciliation process."""
    log.info("Starting Legacy Data Reconciliation Scan...")
    report = ReconReport()
    manager = IngestionManager() # reuse for checksum & DB logic
    
    # 1. Discover all xlsx files in the nest/ hierarchy
    # (Excluding inbox and Quarantine)
    found_files = []
    for r_type, folder in ROUTING_MAP.items():
        folder_path = NEST_DIR / folder
        if folder_path.exists():
            found_files.extend(list(folder_path.glob("*.xlsx")))
    
    # Also scan the root NEST_DIR and inbox/ in case files were dropped there
    found_files.extend(list(NEST_DIR.glob("*.xlsx")))
    found_files.extend(list(settings.inbox_dir.glob("*.xlsx")))

    
    # Filter out temporary Excel files (starting with ~$) and deduplicate
    legacy_files = []
    for f in found_files:
        if not f.name.startswith("~$") and f not in legacy_files:
            legacy_files.append(f)

    legacy_files.sort()
    report.total_scanned = len(legacy_files)
    log.info(f"Found {len(legacy_files)} legacy files to reconcile.")

    for file_path in legacy_files:

        try:
            _handle_legacy_file(file_path, manager, report)
        except Exception as exc:
            log.error(f"Failed to reconcile '{file_path.name}': {exc}")
            # Move to quarantine if we can't even open it
            manager._quarantine_file(file_path, f"Reconciliation Failure: {str(exc)}")
            report.quarantined += 1

    report.print_summary()


def _safe_move(src: Path, dst: Path, retries: int = 5, delay: float = 0.5) -> None:
    """Attempt to move a file with retries to handle Windows file locks."""
    import gc
    gc.collect() # Hint to release any lingering handles
    
    for i in range(retries):
        try:
            shutil.move(str(src), str(dst))
            return
        except PermissionError:
            if i == retries - 1:
                raise
            time.sleep(delay)


def _handle_legacy_file(file_path: Path, manager: IngestionManager, report: ReconReport) -> None:
    """Classify, standardise, and register a single legacy file."""
    log.info(f"Scanning legacy file: {file_path.name}")
    
    # 1. Read raw data first (header=None) to find the best header row
    reader_raw = ExcelReader(file_path, header_row=None)

    try:
        frames_raw = reader_raw.read()
    except Exception as exc:
        log.error(f"Reader error for {file_path.name}: {exc}")
        raise

    if not frames_raw:
        raise ValueError("Excel file contains no readable sheets.")
        
    sheet_name = list(frames_raw.keys())[0]
    df_raw = frames_raw[sheet_name]
    
    # 2. Find the best header row
    header_idx = StructuralClassifier.find_best_header_row(df_raw)
    
    # 3. Slice and build cleaned DataFrame
    df = df_raw.iloc[header_idx:].reset_index(drop=True)
    # Set the row as columns
    df.columns = df.iloc[0]
    df = df.drop(df.index[0]).reset_index(drop=True)
    
    # 4. Normalise headers for classification
    df = normalise_column_names(df)
    
    # 5. Classify and build metadata
    meta = classify_file(df)

    
    if meta.report_type == ReportType.UNKNOWN:
        log.warning(f"Unidentified file content: {file_path.name}")
        manager._quarantine_file(file_path, "Could not identify report type during reconciliation.")
        report.quarantined += 1
        return

    # 2. Routing Validation
    target_dir_name = ROUTING_MAP.get(meta.report_type)
    target_dir = NEST_DIR / target_dir_name
    target_dir.mkdir(exist_ok=True, parents=True)
    new_name = meta.generate_filename()
    final_path = target_dir / new_name
    
    # --- PROTECTION LOGIC ---
    # If the file is ALREADY in its correct home with the correct name, 
    # we MUST protect it even if it's a duplicate in the DB.
    if file_path == final_path:
        log.info(f"Protected: '{file_path.name}' is already in its standardized location. Skipping.")
        report.standardised_correctly += 1
        return

    # 5. Checksum & Idempotency
    checksum = manager._get_checksum(file_path)
    if manager._is_duplicate(checksum):
        # SAFETY FIX v2: We ONLY delete the duplicate if the standardised version ALREADY EXISTS.
        # This prevents deleting the "only" copy of the data just because the DB knows about it.
        if final_path.exists() and file_path != final_path:
            log.warning(f"Duplicate content found for '{file_path.name}'. Removing redundant copy.")
            # Retry loop for removal on Windows
            for i in range(5):
                try:
                    os.remove(file_path)
                    report.duplicates_removed += 1
                    return
                except PermissionError:
                    if i == 4:
                        raise
                    time.sleep(0.5)
                    gc.collect()
        else:
            log.info(f"Duplicate content found for '{file_path.name}', but no standardised copy exists yet. Proceeding with standardisation.")


    # 6. Standardise & Move (for files not yet in their final home)
    target_dir.mkdir(exist_ok=True, parents=True)
    
    # Handle filename collisions in target dir
    if final_path.exists():
        final_path = target_dir / f"{final_path.stem}_{int(time.time())}{final_path.suffix}"
    
    _safe_move(file_path, final_path)
    log.info(f"Standardised: {new_name}")
    report.standardised += 1

    # 6. Register in DB as 'completed'
    manager._record_ingestion(
        original=file_path.name,
        normalized=new_name,
        meta=meta,
        checksum=checksum,
        final_path=final_path
    )
    _update_ingestion_to_completed(checksum)



def _update_ingestion_to_completed(checksum: str) -> None:
    """Mark the newly created record as completed since it's legacy data."""
    from sqlalchemy import update
    with get_session() as session:
        stmt = update(FileIngestionMeta).where(FileIngestionMeta.checksum_sha256 == checksum).values(status="completed")
        session.execute(stmt)


if __name__ == "__main__":
    reconcile_legacy_data()
