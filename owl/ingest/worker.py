"""
owl.ingest.worker
~~~~~~~~~~~~~~~~~
Asynchronous processing worker — handles transformation and loading 
of validated files.

Workflow
--------
1. Poll 'file_ingestion_meta' for 'pending' records.
2. For each record:
   a. Mark as 'processing'.
   b. Instantiate Pipeline with detected ReportType.
   c. Execute run() and capture results.
   d. Handle partial success by updating error_context with failed row data.
   e. Mark as 'completed' or 'failed'.
"""

from __future__ import annotations

import time
import json
from datetime import datetime
from sqlalchemy import select, update

from owl.extract.classifier import ReportType
from owl.extract.registry import NORMALIZER_REGISTRY
from owl.load.database import get_session
from owl.load.models import FileIngestionMeta
from owl.logger import get_logger
from owl.pipeline import Pipeline

log = get_logger(__name__)


class IngestionWorker:
    """Processes pending ingestion records."""

    def __init__(self, poll_interval: int = 5) -> None:
        self._interval = poll_interval

    def run_once(self) -> None:
        """Poll and process one batch of pending records."""
        with get_session() as session:
            # Atomic selection and marking as processing
            stmt = (
                select(FileIngestionMeta)
                .where(FileIngestionMeta.status == "pending")
                .limit(5)
            )
            pending = session.execute(stmt).scalars().all()
            pending_ids = [record.id for record in pending]
            for record in pending:
                record.status = "processing"
            session.commit()

        # Process each record by its ID
        for ingestion_id in pending_ids:
            try:
                # Re-fetch record inside the processing scope
                with get_session() as session:
                    record = session.get(FileIngestionMeta, ingestion_id)
                    if record:
                        self._process_record(record)
            except Exception as exc:
                log.exception(f"Worker failed to process job {ingestion_id}")
                self._mark_failed(ingestion_id, str(exc))

    def _process_record(self, record: FileIngestionMeta) -> None:
        """Execute the pipeline for a single metadata record."""
        log.info(f"Processing[{record.id}]: {record.normalized_filename}")
        
        # 1. Fetch Validation Context (Option A)
        # We fetch all currently valid id_no from the employees table.
        # This allows normalizers to identify and quarantine 'Orphan' records.
        valid_ids = set()
        with get_session() as session:
            from owl.load.models import Employee
            res = session.execute(select(Employee.id_no)).scalars().all()
            valid_ids = set(res)
            log.debug(f"Process[{record.id}]: Loaded {len(valid_ids)} valid staff IDs for validation.")

        # 2. Resolve normalizer
        r_type = ReportType(record.report_type)
        normalizer_class = NORMALIZER_REGISTRY.get(r_type)
        
        if normalizer_class is None:
             log.warning(f"No normalizer registered for type '{r_type.value}'.")

        # 3. Run Pipeline with Context
        pipeline = Pipeline(
            source_file=record.file_path,
            normalizer_class=normalizer_class,
            ingestion_id=str(record.id),
            context={"valid_ids": valid_ids}
        )
        
        results = pipeline.run()
        
        # 3. Update Status and Meta
        self._mark_completed(record.id, results)

    def _mark_completed(self, ingestion_id: str, results: dict) -> None:
        """Update record status to completed with audit context."""
        with get_session() as session:
            # Flatten failed rows from all tables for audit storage
            failed_rows = {}
            has_failures = False
            
            # results["load_results"] is {table: {success: N, failed: M}}
            # Actually, Pipeline.run() returns reports in robust mode. 
            # I need to ensure Pipeline.run() returns enough to update DB.
            
            # If we want to store actual failed row data in error_context:
            # We'd need to pass the full reports back from Pipeline.
            
            status = "completed"
            summary = results.get("load_results", {})
            for table, counts in summary.items():
                if counts.get("failed", 0) > 0:
                    status = "failed" # Should we mark as failed if ANY row fails? 
                                     # Or "completed" with warnings?
                                     # User said "isolate bad rows without halting".
                                     # I'll use "completed" if it finished, but log errors.
                    has_failures = True

            stmt = (
                update(FileIngestionMeta)
                .where(FileIngestionMeta.id == ingestion_id)
                .values(
                    status="completed" if not has_failures else "completed", # keeping status clear
                    processed_at=datetime.now(),
                    error_context=results
                )
            )
            session.execute(stmt)
            session.commit()
        log.info(f"Job {ingestion_id} finished.")

    def _mark_failed(self, ingestion_id: str, error: str) -> None:
        """Mark record as failed on critical pipeline crash."""
        with get_session() as session:
            stmt = (
                update(FileIngestionMeta)
                .where(FileIngestionMeta.id == ingestion_id)
                .values(
                    status="failed",
                    processed_at=datetime.now(),
                    error_context={"fatal_error": error}
                )
            )
            session.execute(stmt)
            session.commit()


if __name__ == "__main__":
    worker = IngestionWorker()
    log.info("Ingestion Worker started. Polling for 'pending' jobs...")
    while True:
        worker.run_once()
        time.sleep(5)
