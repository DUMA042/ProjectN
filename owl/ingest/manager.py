"""
owl.ingest.manager
~~~~~~~~~~~~~~~~~~
Managed Ingestion Service — responsible for classifying, standardising, 
and routing new files.

Workflow
--------
1. Watch 'inbox/' for new Excel files.
2. For each file:
   a. Analyze structure (columns) to identify report type.
   b. If identified, extract period and standardise filename.
   c. Calculate checksum and verify idempotency.
   d. Rename and move to the verified folder in 'nest/'.
   e. Log as 'pending' in 'file_ingestion_meta'.
   f. If failed, move to 'nest/Quarantine/'.
"""

from __future__ import annotations

import hashlib
import shutil
import time
from dataclasses import replace
from pathlib import Path

import pandas as pd

from sqlalchemy import select

from owl.config import settings
from owl.extract.classifier import classify_file, ROUTING_MAP, ReportType, StructuralClassifier

from owl.extract.excel_reader import ExcelReader
from owl.load.database import get_session
from owl.load.models import FileIngestionMeta
from owl.logger import get_logger
from owl.transform.cleaner import normalise_column_names

log = get_logger(__name__)

INBOX_DIR = settings.inbox_dir
QUARANTINE_DIR = settings.nest_dir / "Quarantine"


class IngestionManager:
    """Orchestrates the Managed Ingestion process."""

    def __init__(self, watch_interval: int = 10) -> None:
        self._interval = watch_interval
        INBOX_DIR.mkdir(exist_ok=True)
        QUARANTINE_DIR.mkdir(exist_ok=True, parents=True)

    def run_once(self) -> None:
        """Scan inbox once and process any new files found."""
        files = list(INBOX_DIR.glob("*.xlsx"))
        if not files:
            return

        log.info(f"Detected {len(files)} new file(s) in inbox.")
        for file_path in files:
            try:
                self._process_file(file_path)
            except Exception as exc:
                log.exception(f"Failed to ingest file '{file_path.name}'.")
                
                # FORCE CLEANUP to release file handles on Windows
                import gc
                gc.collect()
                time.sleep(1)
                
                self._quarantine_file(file_path, str(exc))

    def _process_file(self, file_path: Path) -> None:
        """Handle identification, renaming, and routing for a single file."""
        log.info(f"Classifying: {file_path.name}")

        # Warn about large files — full processing may need streaming mode
        size_mb = file_path.stat().st_size / (1024 * 1024)
        if size_mb > settings.max_file_size_mb:
            log.warning(
                f"File '{file_path.name}' is {size_mb:.0f} MB (threshold: "
                f"{settings.max_file_size_mb} MB). Will read in streaming mode "
                f"to avoid memory exhaustion."
            )

        reader_raw = ExcelReader(file_path, header_row=None)
        frames_raw = reader_raw.read()
        
        if not frames_raw:
            raise ValueError("Excel file contains no readable sheets.")
        
        found_meta = None
        found_df = None
        target_sheet = None
        
        for sheet_name, df_raw in frames_raw.items():
            log.debug(f"Checking sheet '{sheet_name}' for report fingerprint...")
            result = StructuralClassifier.find_best_header_row(df_raw)
            if result:
                report_type, header_idx = result
                log.info(f"Matched {report_type.value} on sheet '{sheet_name}' (row {header_idx})")
                
                # Settle on this sheet and extract clean headers
                df = df_raw.iloc[header_idx:].reset_index(drop=True)
                df.columns = df.iloc[0]
                df = df.drop(df.index[0]).reset_index(drop=True)
                
                # 🛡️ LEAVE-SPECIFIC POST-PROCESSING
                # Leave files use a 2-row header structure. After promoting Row 0 to columns,
                # Row 1 (Sub-Header) becomes the first data row. We drop it here.
                if report_type == ReportType.LEAVE and len(df) > 0:
                    log.debug("Leave file detected: Dropping sub-header row from data.")
                    df = df.drop(df.index[0]).reset_index(drop=True)
                
                df = normalise_column_names(df)
                
                found_meta = classify_file(df)
                found_meta = replace(found_meta, report_type=report_type)
                found_df = df
                target_sheet = sheet_name
                break
        
        del frames_raw
        import gc
        gc.collect()

        if not found_meta:
             raise ValueError("Could not identify report type in any sheet of this workbook.")

        target_dir_name = ROUTING_MAP.get(found_meta.report_type)
        if not target_dir_name:
             raise ValueError(f"No routing folder defined for type: {found_meta.report_type}")
        
        target_dir = settings.nest_dir / target_dir_name
        target_dir.mkdir(exist_ok=True, parents=True)
        
        internal_hash = pd.util.hash_pandas_object(found_df, index=False).values.tobytes()
        checksum = hashlib.sha256(internal_hash).hexdigest()

        if self._is_duplicate(checksum):
            log.warning(f"File '{file_path.name}' already exists. Quarantining.")
            self._quarantine_file(file_path, "Duplicate file content.")
            return

        new_name = found_meta.generate_filename()
        final_path = target_dir / new_name
        
        while final_path.exists():
            log.info(f"Filename '{new_name}' already exists. Bumping version...")
            found_meta = replace(found_meta, version=found_meta.version + 1)
            new_name = found_meta.generate_filename()
            final_path = target_dir / new_name
        
        if found_meta.report_type == ReportType.NOMINAL:
            self._rotate_nominal_folder(target_dir)

        self._record_ingestion(file_path.name, new_name, found_meta, checksum, file_path, final_path)

        gc.collect()
        self._safe_move(file_path, final_path)
        log.info(f"Successfully routed '{new_name}' to {target_dir_name}")

    def _record_ingestion(self, original: str, normalized: str, meta, checksum: str, source_path: Path, final_path: Path) -> None:
        """Log the ingestion to the database with 'pending' status."""
        with get_session() as session:
            obj = FileIngestionMeta(
                original_filename=original,
                normalized_filename=normalized,
                department=meta.department,
                report_type=meta.report_type.value,
                version=meta.version,
                file_path=str(final_path),
                checksum_sha256=checksum,
                file_size_bytes=source_path.stat().st_size,
                status="pending"
            )
            session.add(obj)
            session.flush()
            log.debug(f"Recorded ingestion ID: {obj.id}")

    def _safe_move(self, src: Path, dst: Path, retries: int = 10, delay: float = 1.0) -> None:
        """Robustly move a file with retries to handle Windows file locks."""
        import gc
        import time
        
        for i in range(retries):
            try:
                gc.collect()
                time.sleep(0.5) 
                shutil.move(str(src), str(dst))
                return
            except (PermissionError, OSError) as exc:
                if i == retries - 1:
                    log.error(f"Failed to move file after {retries} attempts: {exc}")
                    raise
                log.warning(f"File '{src.name}' is locked. Retrying in {delay}s... (Attempt {i+1}/{retries})")
                time.sleep(delay)

    def _rotate_nominal_folder(self, target_dir: Path) -> None:
        """Move any existing Nominal files to Quarantine to ensure a singleton active file."""
        existing_files = list(target_dir.glob("*.xlsx"))
        if not existing_files:
            return
            
        log.info(f"Rotating Nominal folder: moving {len(existing_files)} file(s) to Quarantine.")
        for f in existing_files:
            self._quarantine_file(f, "Superseded by new Nominal upload", suffix="_SUPERSEDED")

    def _is_duplicate(self, checksum: str) -> bool:
        """Check if this exact file content has been seen before."""
        with get_session() as session:
            stmt = select(FileIngestionMeta).where(FileIngestionMeta.checksum_sha256 == checksum)
            result = session.execute(stmt).scalars().first()
            return result is not None

    def _quarantine_file(self, file_path: Path, reason: str, suffix: str = "") -> None:
        """Move failed or superseded files to the Quarantine folder."""
        log.warning(f"Quarantining '{file_path.name}': {reason}")
        
        timestamp = int(time.time())
        new_name = f"{file_path.stem}_{timestamp}{suffix}{file_path.suffix}"
        dest = QUARANTINE_DIR / new_name
        QUARANTINE_DIR.mkdir(exist_ok=True, parents=True)
        
        self._safe_move(file_path, dest)
        
        try:
            with get_session() as session:
                ingestion = FileIngestionMeta(
                    original_filename=file_path.name,
                    normalized_filename=file_path.name,
                    file_path=str(dest),
                    checksum_sha256="N/A",
                    status="quarantined",
                    error_context={"reason": reason},
                    version=1,
                    file_size_bytes=0,
                )
                session.add(ingestion)
        except Exception:
            log.error("Could not record quarantine status to DB.")


if __name__ == "__main__":
    manager = IngestionManager()
    log.info("Ingestion Manager started. Monitoring 'inbox/'...")
    while True:
        manager.run_once()
        time.sleep(10)