"""In-memory Build job store + stage machine (§23 of the Build spec).

Stages: added → inspected → hashing → validated → sent_to_ai → analysis →
topics_ready → generating → complete. A job also carries per-file states so
the UI can show overall + current-file progress. In-memory by design: a
server restart drops jobs, but manifest files (the data) always survive.
"""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Any

STAGES = (
    "added",
    "inspected",
    "hashing",
    "validated",
    "sent_to_ai",
    "analysis",
    "topics_ready",
    "generating",
    "complete",
    "cancelled",
    # Individual-report pipeline stages (AI flow never uses these).
    "resolving",
    "querying",
    "rendering",
    "failed",
)

FILE_STATES = ("pending", "active", "done", "error")

_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_job(file_ids: list[str]) -> dict[str, Any]:
    job = {
        "id": uuid.uuid4().hex,
        "file_ids": list(file_ids),
        "stage": "added",
        "stage_detail": "",
        "files": [
            {"id": fid, "state": "pending", "error": None} for fid in file_ids
        ],
        "hash_mode": None,
        "cancelled": False,
        "created_at": _now(),
        "updated_at": _now(),
        "payload": {},
    }
    with _lock:
        _jobs[job["id"]] = job
    return job


def get_job(job_id: str) -> dict[str, Any] | None:
    with _lock:
        job = _jobs.get(job_id)
        return dict(job) if job is not None else None


def _mutate(job_id: str, fn) -> dict[str, Any] | None:
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return None
        fn(job)
        job["updated_at"] = _now()
        return dict(job)


def set_stage(job_id: str, stage: str, detail: str = "") -> dict[str, Any] | None:
    if stage not in STAGES:
        raise ValueError(f"Unknown stage '{stage}'")
    return _mutate(job_id, lambda j: (j.update(stage=stage, stage_detail=detail)))


def set_file_state(
    job_id: str, file_id: str, state: str, error: str | None = None
) -> dict[str, Any] | None:
    if state not in FILE_STATES:
        raise ValueError(f"Unknown file state '{state}'")
    def _apply(job: dict[str, Any]) -> None:
        for f in job["files"]:
            if f["id"] == file_id:
                f["state"] = state
                f["error"] = error
    return _mutate(job_id, _apply)


def set_payload(job_id: str, key: str, value: Any) -> dict[str, Any] | None:
    return _mutate(job_id, lambda j: j["payload"].__setitem__(key, value))


def add_files(job_id: str, file_ids: list[str]) -> dict[str, Any] | None:
    """Append tracked files (e.g. roster resolved after job creation)."""
    def _apply(job: dict[str, Any]) -> None:
        known = {f["id"] for f in job["files"]}
        for fid in file_ids:
            if fid not in known:
                job["files"].append({"id": fid, "state": "pending", "error": None})
                known.add(fid)
    return _mutate(job_id, _apply)


def cancel_job(job_id: str) -> dict[str, Any] | None:
    """Mark cancelled (terminal): the flag stops in-flight loops, the stage
    stops polling. Returns None for unknown jobs."""

    def _apply(job: dict[str, Any]) -> None:
        job["cancelled"] = True
        if job["stage"] != "complete":
            job["stage"] = "cancelled"
            job["stage_detail"] = "Build cancelled — created files cleaned up"

    return _mutate(job_id, _apply)


def is_cancelled(job_id: str) -> bool:
    with _lock:
        job = _jobs.get(job_id)
        return bool(job and job.get("cancelled"))
