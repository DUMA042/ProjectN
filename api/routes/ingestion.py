"""Ingestion endpoints — multi-file upload, live status polling,
processing details, and upload-record removal (forget)."""
import asyncio
import re
import shutil
import threading
import time
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from api.dependencies import get_db
from owl.config import settings
from owl.ingest.progress import get_progress as get_store_progress
from owl.ingest.manager import IngestionManager
from owl.ingest.worker import IngestionWorker
from owl.load.database import get_session
from owl.load.models import FileIngestionMeta

router = APIRouter(tags=["ingestion"])
INBOX_DIR = settings.inbox_dir

# ── Stage labels shown in the UI ─────────────────────────────────────────────
STAGE_LABELS = {
    "extract": "Extracting data from Excel",
    "transform": "Transforming and cleaning data",
    "validate": "Validating rows against contracts",
    "load": "Loading data into database",
    "parse": "Parsing leave rows",
    "row": "Processing employee rows",
    "start": "Starting…",
}


def _run_worker_background(max_rounds: int = 25) -> None:
    """Run the ingestion worker until no pending records remain.

    Executed on a daemon thread so the HTTP response can return immediately.
    """
    try:
        worker = IngestionWorker()
        for _ in range(max_rounds):
            worker.run_once()
            with get_session() as session:
                remaining = session.execute(
                    select(func.count()).select_from(FileIngestionMeta)
                    .where(FileIngestionMeta.status == "pending")
                ).scalar()
            if not remaining:
                break
    except Exception:  # noqa: BLE001 — background thread must never crash the app
        import logging
        logging.getLogger("owl.ingest.background").exception("Background worker crashed.")


def _stage_info(db_status, progress) -> dict:
    """Build a normalized stage payload for the frontend."""
    if db_status == "completed":
        return {"label": "Processing complete", "percent": 100, "current": None, "total": None}
    if db_status == "failed":
        return {"label": "Processing failed", "percent": None, "current": None, "total": None}
    if db_status == "quarantined":
        return {"label": "File quarantined", "percent": None, "current": None, "total": None}
    if db_status == "pending":
        return {"label": "Waiting for worker…", "percent": None, "current": None, "total": None}

    # processing (or unknown) → derive from progress store
    if progress and isinstance(progress, dict):
        stage = progress.get("stage")
        label = STAGE_LABELS.get(stage, "Processing data")
        current = progress.get("current")
        total = progress.get("total")
        percent = None
        if isinstance(current, (int, float)) and isinstance(total, (int, float)) and total > 0:
            percent = round((current / total) * 100)
            label = f"{label}… {current:,}/{total:,}"
        return {"label": label, "percent": percent, "current": current, "total": total}

    return {"label": "Processing data", "percent": None, "current": None, "total": None}


@router.post("/ingest/upload")
async def ingest_upload(files: List[UploadFile] = File(..., description="One or more .xlsx files")):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    if len(files) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 files per upload")

    results = []
    rejected = []

    for file in files:
        original_name = file.filename or "unnamed.xlsx"
        try:
            if not original_name.lower().endswith(".xlsx"):
                rejected.append({"filename": original_name, "reason": "Only .xlsx files accepted"})
                continue

            # Sanitise: strip any path components / unsafe chars, prefix timestamp
            safe_stem = re.sub(r"[^\w\-. ]", "_", Path(original_name).stem).strip() or "file"
            safe_name = f"{int(time.time())}_{safe_stem}.xlsx"

            INBOX_DIR.mkdir(exist_ok=True)
            dest = INBOX_DIR / safe_name
            with open(dest, "wb") as fh:
                shutil.copyfileobj(file.file, fh)

            manager = IngestionManager()
            await asyncio.to_thread(manager.run_once)

            # Extract all needed values INSIDE the session — the ORM instance
            # is expired/detached once the context manager commits and closes.
            with get_session() as session:
                record = session.execute(
                    select(FileIngestionMeta)
                    .where(FileIngestionMeta.original_filename == safe_name)
                    .order_by(FileIngestionMeta.created_at.desc())
                ).scalars().first()

                if record:
                    results.append({
                        "ingestion_id": str(record.id),
                        "original_filename": original_name,
                        "normalized_filename": record.normalized_filename,
                        "report_type": record.report_type,
                        "status": record.status,
                        "quarantine_reason": (record.error_context or {}).get("reason")
                            if isinstance(record.error_context, dict) else None,
                    })
                else:
                    results.append({
                        "ingestion_id": None,
                        "original_filename": original_name,
                        "status": "classification_failed",
                    })
        except Exception as exc:  # noqa: BLE001 — one bad file must not fail the batch
            results.append({
                "ingestion_id": None,
                "original_filename": original_name,
                "status": "classification_failed",
                "error": str(exc),
            })

    # Kick off processing on a daemon thread; HTTP returns immediately so the
    # frontend can poll per-file stage progress via /ingest/status/{id}.
    thread = threading.Thread(target=_run_worker_background, daemon=True)
    thread.start()

    return {"results": results, "rejected": rejected}


@router.get("/ingest/status/{ingestion_id}")
def ingest_status(ingestion_id: str, db: Session = Depends(get_db)):
    progress = get_store_progress(ingestion_id)

    db_status = None
    db_error = None
    filename = None
    report_type = None
    try:
        record = db.get(FileIngestionMeta, uuid.UUID(ingestion_id))
    except ValueError:
        record = None
    if record:
        db_status = record.status
        filename = record.normalized_filename or record.original_filename
        report_type = record.report_type
        if record.error_context:
            db_error = record.error_context

    return {
        "ingestion_id": ingestion_id,
        "db_status": db_status,
        "filename": filename,
        "report_type": report_type,
        "stage_info": _stage_info(db_status, progress),
        "error_context": db_error,
    }


def _extract_failed_rows(ctx: dict) -> list[dict]:
    """Flatten every kind of failure recorded in error_context into row dicts."""
    failed_rows: list[dict] = []
    if not isinstance(ctx, dict):
        return failed_rows

    if ctx.get("fatal_error"):
        failed_rows.append({"row": "—", "id_no": "—", "field": "fatal", "message": ctx["fatal_error"]})

    for item in ctx.get("failed_id_nos", []) or []:
        if isinstance(item, dict):
            failed_rows.append({
                "row": item.get("row", "?"),
                "id_no": item.get("id_no", "?"),
                "field": item.get("field", "—"),
                "message": item.get("reason") or item.get("message") or str(item),
            })

    load_results = ctx.get("load_results", {})
    if isinstance(load_results, dict):
        for table, counts in load_results.items():
            if not (isinstance(counts, dict) and counts.get("failed", 0) > 0):
                continue
            for fr in counts.get("failed_rows", []) or []:
                failed_rows.append({
                    "row": fr.get("row", "?"),
                    "id_no": fr.get("id_no", "?"),
                    "field": fr.get("field", table),
                    "message": fr.get("message", fr.get("error", str(fr))),
                })
            if not counts.get("failed_rows"):
                failed_rows.append({
                    "row": "—", "id_no": "—", "field": table,
                    "message": f"{counts['failed']} record(s) failed to load",
                })

    validation = ctx.get("validation_results", {})
    if isinstance(validation, dict):
        for table, errors in (validation.get("errors_by_table", {}) or {}).items():
            for err in errors or []:
                failed_rows.append({
                    "row": err.get("row_index", err.get("row", "?")),
                    "id_no": err.get("id_no", "—"),
                    "field": err.get("field", table),
                    "message": err.get("message", str(err)),
                })

    for warn in ctx.get("failures", []) or []:
        if isinstance(warn, dict):
            failed_rows.append({
                "row": warn.get("row", warn.get("row_idx", "—")),
                "id_no": warn.get("staff_id", warn.get("id_no", "—")),
                "field": warn.get("type", "failure"),
                "message": warn.get("message", str(warn)),
            })

    if ctx.get("reason") and not failed_rows:
        failed_rows.append({"row": "—", "id_no": "—", "field": "reason", "message": ctx["reason"]})

    return failed_rows


@router.get("/ingest/{ingestion_id}/details")
def ingest_details(ingestion_id: str, db: Session = Depends(get_db)):
    try:
        uid = uuid.UUID(ingestion_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ingestion ID")

    record = db.get(FileIngestionMeta, uid)
    if not record:
        raise HTTPException(status_code=404, detail="Ingestion not found")

    ctx = record.error_context or {}
    if not isinstance(ctx, dict):
        ctx = {}

    tables_breakdown = []
    rows_loaded = rows_failed = 0
    load_results = ctx.get("load_results", {})
    if isinstance(load_results, dict):
        for table, counts in load_results.items():
            if isinstance(counts, dict) and ("success" in counts or "failed" in counts):
                added = counts.get("success", 0) or 0
                failed = counts.get("failed", 0) or 0
                tables_breakdown.append({"table": table, "rows_added": added, "rows_failed": failed})
                rows_loaded += added
                rows_failed += failed

    validation_rejected = 0
    validation = ctx.get("validation_results", {})
    if isinstance(validation, dict):
        validation_rejected = validation.get("total_rejected", 0) or 0

    duration_seconds = None
    if record.processed_at and record.created_at:
        duration_seconds = round((record.processed_at - record.created_at).total_seconds(), 1)

    processor_report = None
    if any(k in ctx for k in ("total_rows_read", "total_successes", "warnings")):
        processor_report = {
            "rows_read": ctx.get("total_rows_read"),
            "successes": ctx.get("total_successes"),
            "partial_successes": ctx.get("total_partial_successes"),
            "failures": ctx.get("total_failures"),
            "updates": ctx.get("total_updates"),
            "new_inserts": ctx.get("total_new_inserts"),
            "warning_count": len(ctx.get("warnings", []) or []),
            "failure_count": len(ctx.get("failures", []) or []),
        }

    # ── Failure rows: breakdown grouping + sample cap (user sampling rule) ──
    all_failed = _extract_failed_rows(ctx)
    failed_rows_total = len(all_failed)

    breakdown_map: dict[str, int] = {}
    for r in all_failed:
        msg = re.sub(r"\d+", "#", str(r.get("message", "")))[:90]
        key = f"{r.get('field', '—')} · {msg}"
        breakdown_map[key] = breakdown_map.get(key, 0) + 1
    failure_breakdown = [
        {"reason": k, "count": v}
        for k, v in sorted(breakdown_map.items(), key=lambda kv: -kv[1])
    ]

    SAMPLE_CAP = 500
    failed_rows_sample = all_failed[:SAMPLE_CAP]

    return {
        "ingestion_id": ingestion_id,
        "filename": record.normalized_filename or record.original_filename,
        "original_filename": record.original_filename,
        "report_type": record.report_type,
        "status": record.status,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "processed_at": record.processed_at.isoformat() if record.processed_at else None,
        "duration_seconds": duration_seconds,
        "summary": {
            "rows_loaded": rows_loaded,
            "rows_failed": rows_failed,
            "validation_rejected": validation_rejected,
        },
        "tables_breakdown": tables_breakdown,
        "processor_report": processor_report,
        "failed_rows_total": failed_rows_total,
        "failure_breakdown": failure_breakdown,
        "failed_rows": failed_rows_sample,
    }


@router.get("/ingest/{ingestion_id}/errors")
def ingest_errors(ingestion_id: str, db: Session = Depends(get_db)):
    try:
        uid = uuid.UUID(ingestion_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ingestion ID")

    record = db.get(FileIngestionMeta, uid)
    if not record:
        raise HTTPException(status_code=404, detail="Ingestion not found")

    failed_rows = _extract_failed_rows(record.error_context or {})
    return {"ingestion_id": ingestion_id, "total_failed": len(failed_rows), "failed_rows": failed_rows}


@router.post("/ingest/{ingestion_id}/forget")
def forget_ingestion(ingestion_id: str, db: Session = Depends(get_db)):
    """Remove only the upload tracking record so the same file can be re-uploaded.

    Data already loaded into the database is intentionally left untouched.
    """
    try:
        uid = uuid.UUID(ingestion_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ingestion ID")

    record = db.get(FileIngestionMeta, uid)
    if not record:
        raise HTTPException(status_code=404, detail="Ingestion not found")

    filename = record.normalized_filename or record.original_filename
    db.delete(record)
    db.commit()

    return {
        "status": "ok",
        "filename": filename,
        "message": f"Upload record removed. '{filename}' can now be re-uploaded.",
    }


@router.get("/ingest/history")
def ingest_history(db: Session = Depends(get_db), limit: int = Query(50, ge=1, le=200)):
    rows = db.execute(
        select(FileIngestionMeta).order_by(FileIngestionMeta.created_at.desc()).limit(limit)
    ).scalars().all()
    return [
        {
            "id": str(r.id),
            "original_filename": r.original_filename,
            "normalized_filename": r.normalized_filename,
            "report_type": r.report_type,
            "status": r.status,
            "error_context": r.error_context,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "processed_at": r.processed_at.isoformat() if r.processed_at else None,
        }
        for r in rows
    ]
