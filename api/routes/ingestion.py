"""Ingestion endpoints — multi-file upload, status polling, error details, history."""
import asyncio
import shutil
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from api.dependencies import get_db
from owl.config import settings
from owl.ingest.progress import get_progress as get_store_progress
from owl.ingest.manager import IngestionManager
from owl.ingest.worker import IngestionWorker
from owl.load.models import FileIngestionMeta

router = APIRouter(tags=["ingestion"])
INBOX_DIR = settings.inbox_dir


@router.post("/ingest/upload")
async def ingest_upload(files: List[UploadFile] = File(..., description="One or more .xlsx files")):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    results = []
    rejected = []

    for file in files:
        if not file.filename or not file.filename.lower().endswith(".xlsx"):
            rejected.append({"filename": file.filename, "reason": "Only .xlsx files accepted"})
            continue

        INBOX_DIR.mkdir(exist_ok=True)
        dest = INBOX_DIR / file.filename
        with open(dest, "wb") as fh:
            shutil.copyfileobj(file.file, fh)

        manager = IngestionManager()
        await asyncio.to_thread(manager.run_once)

        from owl.load.database import get_session
        with get_session() as session:
            record = session.execute(
                select(FileIngestionMeta)
                .where(FileIngestionMeta.original_filename == file.filename)
                .order_by(FileIngestionMeta.created_at.desc())
            ).scalars().first()

        if record:
            results.append({
                "ingestion_id": str(record.id),
                "original_filename": record.original_filename,
                "normalized_filename": record.normalized_filename,
                "report_type": record.report_type,
                "status": record.status,
            })
        else:
            results.append({
                "ingestion_id": None,
                "original_filename": file.filename,
                "status": "classification_failed",
            })

    worker = IngestionWorker()
    asyncio.create_task(asyncio.to_thread(worker.run_once))

    return {"results": results, "rejected": rejected}


@router.get("/ingest/status/{ingestion_id}")
def ingest_status(ingestion_id: str, db: Session = Depends(get_db)):
    progress = get_store_progress(ingestion_id)
    record = db.get(FileIngestionMeta, uuid.UUID(ingestion_id) if ingestion_id else None)

    db_status = None
    db_error = None
    if record:
        db_status = record.status
        if record.error_context:
            db_error = record.error_context

    return {
        "ingestion_id": ingestion_id,
        "db_status": db_status,
        "progress": progress,
        "error_context": db_error,
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

    ctx = record.error_context or {}

    failed_rows = []

    if "fatal_error" in ctx:
        failed_rows.append({"row": 0, "id_no": "N/A", "field": "fatal", "message": ctx["fatal_error"]})

    if "failed_id_nos" in ctx:
        for item in ctx["failed_id_nos"]:
            failed_rows.append({
                "row": item.get("row", "?"),
                "id_no": item.get("id_no", "?"),
                "field": item.get("field", "?"),
                "message": item.get("reason", str(item)),
            })

    load_results = ctx.get("load_results", {})
    if isinstance(load_results, dict):
        for table, counts in load_results.items():
            if isinstance(counts, dict) and counts.get("failed", 0) > 0:
                if "failed_rows" in counts:
                    for fr in counts["failed_rows"]:
                        failed_rows.append({
                            "row": fr.get("row", "?"),
                            "id_no": fr.get("id_no", "?"),
                            "field": fr.get("field", table),
                            "message": fr.get("message", fr.get("error", str(fr))),
                        })
                else:
                    failed_rows.append({
                        "row": "—",
                        "id_no": "—",
                        "field": table,
                        "message": f"{counts['failed']} records failed",
                    })

    validation = ctx.get("validation_results", {})
    if isinstance(validation, dict):
        for table, errors in validation.get("errors_by_table", {}).items():
            for err in (errors or []):
                failed_rows.append({
                    "row": err.get("row", "?"),
                    "id_no": err.get("id_no", "?"),
                    "field": err.get("field", table),
                    "message": err.get("message", str(err)),
                })

    if "reason" in ctx and not failed_rows:
        failed_rows.append({"row": "—", "id_no": "—", "field": "reason", "message": ctx["reason"]})

    return {"ingestion_id": ingestion_id, "total_failed": len(failed_rows), "failed_rows": failed_rows}


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
