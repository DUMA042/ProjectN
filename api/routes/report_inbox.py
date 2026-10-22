"""Report Builder inbox — files sent via 'Send to Report', stored server-side.

Storage is a git-ignored directory (``report_inbox/``) holding the CSV files
plus a ``manifest.json`` index. Filenames are sanitized and timestamp-suffixed
so repeats never overwrite each other. Retention is manual (delete endpoint).
"""
from __future__ import annotations

import csv
import io
import json
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from owl.config import settings

router = APIRouter(tags=["report-inbox"])

MANIFEST_NAME = "manifest.json"
MAX_CSV_BYTES = 25 * 1024 * 1024


class ManifestCorrupt(Exception):
    """Raised when manifest.json exists but cannot be parsed."""


def load_manifest_or_500(base: Path | None = None) -> list[dict[str, Any]]:
    """load_manifest that converts corruption into a loud HTTP 500."""
    try:
        return load_manifest(base)
    except ManifestCorrupt as exc:
        raise HTTPException(status_code=500, detail=str(exc))

_lock = threading.Lock()


def inbox_dir() -> Path:
    d = Path(settings.report_inbox_dir)
    d.mkdir(parents=True, exist_ok=True)
    return d


def manifest_path(base: Path | None = None) -> Path:
    return (base or inbox_dir()) / MANIFEST_NAME


def sanitize_stem(name: str) -> str:
    """Original filename -> safe stem (no path components / unsafe chars)."""
    stem = Path(name or "").stem.strip()
    stem = re.sub(r"[^\w\-. ]", "_", stem).strip() or "file"
    return stem[:80]


def stored_name(stem: str, now: datetime | None = None) -> str:
    """Unique stored filename: repeats coexist, sent time disambiguates."""
    ts = (now or datetime.now(timezone.utc)).strftime("%Y%m%d-%H%M%S")
    return f"{stem}_{ts}.csv"


def load_manifest(base: Path | None = None) -> list[dict[str, Any]]:
    mp = manifest_path(base)
    if not mp.exists():
        return []
    try:
        data = json.loads(mp.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        # Never silently pretend the inbox is empty: the CSVs are still on
        # disk, but the index is unreadable. Loud failure with recovery path.
        raise ManifestCorrupt(
            f"Report index file is corrupted ({mp.name}). Your files are "
            f"still stored — restore {mp.name} from backup or delete it to "
            f"start fresh (stored files themselves are never touched)."
        ) from exc
    return data if isinstance(data, list) else []


def save_manifest(items: list[dict[str, Any]], base: Path | None = None) -> None:
    """Atomic write (temp + rename) so readers never see a half file."""
    mp = manifest_path(base)
    mp.parent.mkdir(parents=True, exist_ok=True)
    tmp = mp.with_suffix(".tmp")
    tmp.write_text(json.dumps(items, indent=2), encoding="utf-8")
    tmp.replace(mp)


def count_rows(csv_text: str) -> int:
    lines = [ln for ln in csv_text.splitlines() if ln.strip()]
    return max(0, len(lines) - 1)  # minus header


# Normalized headers identifying an Employee-ID column. "ID Hint" and bare
# names are deliberately NOT here: only real staff identifiers qualify.
ID_HEADERS = {"idno", "employeeid"}


def header_cells(csv_text: str) -> list[str]:
    """First-row headers, robust to BOM and quoted commas."""
    try:
        reader = csv.reader(io.StringIO(csv_text.lstrip("\ufeff")))
        return next(reader, [])
    except (csv.Error, UnicodeError):
        return []


def classify_csv(csv_text: str) -> str:
    """'individual' if any header is an Employee-ID column, else 'non_individual'."""
    for h in header_cells(csv_text):
        if re.sub(r"[\s_]+", "", str(h).strip().lower()) in ID_HEADERS:
            return "individual"
    return "non_individual"


class InboxRequest(BaseModel):
    filename: str
    source: str = ""
    csv_text: str


@router.post("/reports/inbox")
def inbox_send(body: InboxRequest):
    if not body.csv_text.strip():
        raise HTTPException(status_code=400, detail="Empty CSV content")
    if len(body.csv_text.encode("utf-8")) > MAX_CSV_BYTES:
        raise HTTPException(status_code=400, detail="CSV too large (max 25 MB)")
    stem = sanitize_stem(body.filename)
    display_name = f"{stem}.csv"
    with _lock:
        base = inbox_dir()
        name = stored_name(stem)
        # Timestamp collision within the same second: append a short suffix.
        if (base / name).exists():
            name = f"{stem}_{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')}.csv"
        (base / name).write_text(body.csv_text, encoding="utf-8")
        entry = {
            "id": uuid.uuid4().hex,
            "display_name": display_name,
            "stored_name": name,
            "source": body.source or "export",
            "row_count": count_rows(body.csv_text),
            "byte_size": len(body.csv_text.encode("utf-8")),
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "status": "inbox",
            "moved_at": None,
            "classification": classify_csv(body.csv_text),
        }
        items = load_manifest_or_500(base)
        items.append(entry)
        save_manifest(items, base)
    return entry


@router.get("/reports/inbox")
def inbox_list():
    with _lock:
        base = inbox_dir()
        items = load_manifest_or_500(base)
        # Write-through backfill: legacy entries without a classification get
        # one from the stored file, so old files show a type with no migration.
        dirty = False
        for e in items:
            if not e.get("classification"):
                try:
                    text = (base / e.get("stored_name", "")).read_text(encoding="utf-8-sig")
                    e["classification"] = classify_csv(text)
                except OSError:
                    e["classification"] = "non_individual"
                dirty = True
        if dirty:
            save_manifest(items, base)
    return {"files": list(reversed(items))}


@router.get("/reports/inbox/{file_id}/download")
def inbox_download(file_id: str):
    with _lock:
        items = load_manifest_or_500()
    entry = next((e for e in items if e.get("id") == file_id), None)
    if not entry:
        raise HTTPException(status_code=404, detail="File not found")
    path = inbox_dir() / entry["stored_name"]
    if not path.exists():
        raise HTTPException(status_code=404, detail="Stored file missing")
    return FileResponse(str(path), media_type="text/csv", filename=entry["display_name"])


class MoveRequest(BaseModel):
    status: str


@router.post("/reports/inbox/{file_id}/move")
def inbox_move(file_id: str, body: MoveRequest):
    if body.status not in ("inbox", "build"):
        raise HTTPException(status_code=400, detail="status must be 'inbox' or 'build'")
    with _lock:
        base = inbox_dir()
        items = load_manifest_or_500(base)
        entry = next((e for e in items if e.get("id") == file_id), None)
        if not entry:
            raise HTTPException(status_code=404, detail="File not found")
        entry["status"] = body.status
        entry["moved_at"] = datetime.now(timezone.utc).isoformat()
        save_manifest(items, base)
    return entry


@router.delete("/reports/inbox/{file_id}")
def inbox_delete(file_id: str):
    with _lock:
        base = inbox_dir()
        items = load_manifest_or_500(base)
        kept = [e for e in items if e.get("id") != file_id]
        if len(kept) == len(items):
            raise HTTPException(status_code=404, detail="File not found")
        dropped = [e for e in items if e.get("id") == file_id][0]
        try:
            (base / dropped["stored_name"]).unlink(missing_ok=True)
        except OSError:
            pass
        save_manifest(kept, base)
    return {"deleted": file_id}
