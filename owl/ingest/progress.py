"""
owl.ingest.progress
~~~~~~~~~~~~~~~~~~~
Thread-safe progress store for SSE streaming of ingestion status.

Usage
-----
    from owl.ingest.progress import set_progress, get_progress, clear_progress

    set_progress(ingestion_id, "extract", 500, 2000)
    status = get_progress(ingestion_id)  # {"stage": "extract", "current": 500, "total": 2000}
"""

from __future__ import annotations

from collections.abc import Callable
from threading import Lock
from typing import Any

_lock = Lock()
_store: dict[str, dict[str, Any]] = {}
_MAX_ENTRIES = 500


def _prune_locked() -> None:
    """Drop the oldest entries when the store exceeds _MAX_ENTRIES.

    Must be called while holding _lock. Dicts preserve insertion order,
    so the first keys are the oldest.
    """
    if len(_store) > _MAX_ENTRIES:
        excess = len(_store) - _MAX_ENTRIES
        for key in list(_store.keys())[:excess]:
            _store.pop(key, None)


def make_callback(ingestion_id: str) -> Callable[[str, int, int], None]:
    """Create a progress callback bound to *ingestion_id*.

    Returns a callable suitable for passing to processors:
        callback(stage: str, current: int, total: int)

    This writes directly into the module-level store so the SSE endpoint
    can read it without any database round-trip.
    """

    def on_progress(stage: str, current: int, total: int) -> None:
        with _lock:
            _store[ingestion_id] = {
                "stage": stage,
                "current": current,
                "total": total,
            }
            _prune_locked()

    return on_progress


def set_progress(ingestion_id: str, stage: str, current: int, total: int) -> None:
    """Thread-safe write to the progress store."""
    with _lock:
        _store[ingestion_id] = {
            "stage": stage,
            "current": current,
            "total": total,
        }
        _prune_locked()


def get_progress(ingestion_id: str) -> dict[str, Any] | None:
    """Thread-safe read from the progress store."""
    with _lock:
        return _store.get(ingestion_id)


def set_completed(ingestion_id: str, status: str) -> None:
    """Mark ingestion as completed or failed."""
    with _lock:
        if ingestion_id in _store:
            _store[ingestion_id]["status"] = status
        else:
            _store[ingestion_id] = {"stage": "done", "current": 1, "total": 1, "status": status}
        _prune_locked()


def clear_progress(ingestion_id: str) -> None:
    """Remove an ingestion from the store (call after SSE connection closes)."""
    with _lock:
        _store.pop(ingestion_id, None)
