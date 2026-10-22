"""Shutdown coordination: the worker stops between records and requeues work."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from owl.ingest import worker as worker_module
from owl.load.database import get_session


@pytest.fixture(autouse=True)
def reset_signal():
    worker_module.clear_stop()
    yield
    worker_module.clear_stop()


def _pg():
    try:
        with get_session() as s:
            s.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"local PostgreSQL unavailable: {exc}")


def _insert_pending(label: str) -> tuple[str, str]:
    """Insert one synthetic row; returns (checksum, row id)."""
    tag = f"{label}-{uuid.uuid4().hex[:6]}"
    checksum = f"test-{tag}"
    with get_session() as s:
        row_id = s.execute(
            text(
                "INSERT INTO file_ingestion_meta (id, original_filename, "
                "normalized_filename, file_path, checksum_sha256, status) "
                "VALUES (gen_random_uuid(), :fn, :norm, :fn, :cs, 'pending') "
                "RETURNING id"
            ),
            {"fn": f"test_{tag}.xlsx", "norm": f"t_{tag}_20260801_x.xlsx", "cs": checksum},
        ).scalar()
    return checksum, str(row_id)


def test_stop_signal_requeues_claimed_work(monkeypatch):
    _pg()
    checksum, row_id = _insert_pending("stop")

    # Deterministic claim: only our row, marked processing as the real claim does.
    def claim_only(session, limit: int = 5):
        session.execute(
            text("UPDATE file_ingestion_meta SET status='processing' WHERE id = :i"),
            {"i": row_id},
        )
        return [uuid.UUID(row_id)]

    monkeypatch.setattr(worker_module, "claim_pending", claim_only)

    def must_not_process(self, record):  # noqa: ANN001
        raise AssertionError("record must not be processed after stop")

    monkeypatch.setattr(worker_module.IngestionWorker, "_process_record", must_not_process)
    worker_module.request_stop()

    worker_module.IngestionWorker().run_once()

    with get_session() as s:
        status = s.execute(
            text("SELECT status FROM file_ingestion_meta WHERE checksum_sha256 = :cs"),
            {"cs": checksum},
        ).scalar()
    assert status == "pending", "interrupted job must be handed back"


def test_wait_for_idle_reports_completion():
    import threading

    done = []

    def work():
        done.append(1)

    thread = threading.Thread(target=work)
    worker_module.register_thread(thread)
    thread.start()
    assert worker_module.wait_for_idle(timeout=5.0) is True
    assert done == [1]
