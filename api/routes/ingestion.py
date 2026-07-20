"""Ingestion endpoints — file upload + SSE progress streaming."""

import asyncio
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sse_starlette.sse import EventSourceResponse
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
async def ingest_upload(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx files are accepted")

    INBOX_DIR.mkdir(exist_ok=True)
    dest = INBOX_DIR / file.filename
    with open(dest, "wb") as fh:
        shutil.copyfileobj(file.file, fh)

    manager = IngestionManager()
    await asyncio.to_thread(manager.run_once)

    from owl.ingest.worker import IngestionWorker
    worker = IngestionWorker()
    asyncio.create_task(_process_async())

    return {"message": "File received", "filename": file.filename}


async def _process_async():
    worker = IngestionWorker()
    await asyncio.to_thread(worker.run_once)


@router.get("/ingest/status/{ingestion_id}")
async def ingest_status(ingestion_id: str):
    async def event_stream():
        while True:
            data = get_store_progress(ingestion_id)
            if data is None:
                yield {"event": "waiting", "data": "No progress yet"}
            elif data.get("status") == "completed":
                yield {"event": "complete", "data": str(data)}
                break
            elif data.get("status") == "failed":
                yield {"event": "error", "data": str(data)}
                break
            else:
                yield {"event": "progress", "data": str(data)}
            await asyncio.sleep(1)

    return EventSourceResponse(event_stream())


@router.get("/ingest/history")
def ingest_history(db: Session = Depends(get_db), limit: int = 20):
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
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "processed_at": r.processed_at.isoformat() if r.processed_at else None,
        }
        for r in rows
    ]
