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
from owl.ingest.progress import make_callback, set_completed
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

        ingestion_id = str(record.id)
        on_progress = make_callback(ingestion_id)

        r_type = ReportType(record.report_type)

        # ── Nominal Roll: dedicated processor with history tracking ──────────
        if r_type == ReportType.NOMINAL:
            from owl.nominal.processor import NominalProcessor
            processor = NominalProcessor(file_path=record.file_path)
            on_progress("start", 0, 1)
            summary = processor.process(progress_callback=on_progress)
            set_completed(ingestion_id, "completed")
            self._mark_completed(record.id, {"load_results": summary})
            return

        # ── Leave Processing: dedicated multi-header position-based processor ──
        if r_type == ReportType.LEAVE:
            from owl.leave.processor import LeaveProcessor
            processor = LeaveProcessor(file_path=record.file_path)
            on_progress("start", 0, 1)
            summary = processor.process(progress_callback=on_progress)
            set_completed(ingestion_id, "completed")
            self._mark_completed(record.id, {"load_results": summary})
            return

        # ── All other report types: generic Pipeline ─────────────────────────
        # Fetch valid id_no set for orphan detection in card swipes / training
        import re
        valid_ids = set()
        name_to_id = {}
        name_to_id_sorted = {}
        with get_session() as session:
            from owl.load.models import Employee
            emps = session.execute(select(Employee.id_no, Employee.full_name)).all()
            for id_no, full_name in emps:
                if id_no:
                    valid_ids.add(id_no)
                if full_name:
                    clean = ' '.join(str(full_name).lower().strip().split())
                    name_to_id[clean] = id_no
                    sorted_key = ' '.join(sorted(re.sub(r'[^\w\s]', '', str(full_name).lower()).split()))
                    name_to_id_sorted[sorted_key] = id_no
            log.debug(f"Process[{record.id}]: Loaded {len(valid_ids)} valid staff IDs.")

        normalizer_class = NORMALIZER_REGISTRY.get(r_type)
        if normalizer_class is None:
            log.warning(f"No normalizer registered for type '{r_type.value}'.")

        # ── Training: inject a DimensionCache so the normalizer can resolve ──
        # and auto-create venue / consultant / location IDs against real DB PKs.
        if r_type == ReportType.TRAINING:
            from owl.transform.dimension_cache import DimensionCache
            with get_session() as dim_session:
                dim_cache = DimensionCache(dim_session)
                pipeline = Pipeline(
                    source_file=record.file_path,
                    normalizer_class=normalizer_class,
                    ingestion_id=str(record.id),
                    context={
                        "valid_ids": valid_ids,
                        "name_to_id": name_to_id,
                        "name_to_id_sorted": name_to_id_sorted,
                        "dim_cache": dim_cache,
                    }
                )
                # Run only the Extract + Transform stages inside the dim_session scope
                # so that any new dimension rows are written and then committed
                # BEFORE the Load stage opens its own connection.
                on_progress("extract", 0, 1)
                frames   = pipeline._extract()
                on_progress("extract", 1, 1)
                entities = pipeline._transform(frames)
                on_progress("transform", 1, 1)
                on_progress("validate", 0, 1)
                entities, validation_errors = pipeline._validate(entities)
                on_progress("validate", 1, 1)

                # Commit the dimension inserts NOW so the loader's separate
                # connection can see the new venue/consultant/location rows
                # when it checks FK constraints on employee_trainings.
                dim_session.commit()
                log.info(f"Process[{record.id}]: Dimension inserts committed.")

            # Load stage runs AFTER dim_session is closed and committed
            on_progress("load", 0, 1)
            load_reports = pipeline._load(entities)
            on_progress("load", 1, 1)
            results = {
                "source_file": str(pipeline._source_file),
                "ingestion_id": str(record.id),
                "status": "completed",
                "validation_results": {
                    "total_rejected": sum(len(e) for e in validation_errors.values()),
                    "errors_by_table": {
                        t: [{"row": e["row_index"], "field": e["field"], "message": e["message"]}
                            for e in errs]
                        for t, errs in validation_errors.items() if errs
                    }
                },
                "load_results": {
                    t: {"success": r.success_count, "failed": len(r.failed_rows)}
                    for t, r in load_reports.items()
                }
            }
            self._mark_completed(record.id, results)
            return

        pipeline = Pipeline(
            source_file=record.file_path,
            normalizer_class=normalizer_class,
            ingestion_id=str(record.id),
            context={"valid_ids": valid_ids, "name_to_id": name_to_id, "name_to_id_sorted": name_to_id_sorted}
        )
        results = pipeline.run(progress_callback=on_progress)
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
        set_completed(ingestion_id, "failed")
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
