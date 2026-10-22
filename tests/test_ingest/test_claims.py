"""Ingestion claim + sweep semantics (needs local PostgreSQL, else skips).

- claim_pending skips rows locked by a concurrent worker (SKIP LOCKED).
- The startup sweep uses updated_at: recently-touched jobs survive even
  when created long ago; untouched ones are recovered as failed.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from owl.ingest.worker import claim_pending
from owl.load.database import get_session


def _pg():
    try:
        with get_session() as s:
            s.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        pytest.skip(f"local PostgreSQL unavailable: {exc}")
    return False


def _insert_pending(label: str) -> str:
    """Insert one synthetic pending row; returns its tag for lookup/cleanup."""
    tag = f"{label}-{uuid.uuid4().hex[:6]}"
    with get_session() as s:
        # normalized_filename must satisfy the generated period column
        # (3rd underscore part YYYYMMDD).
        s.execute(
            text(
                "INSERT INTO file_ingestion_meta (id, original_filename, "
                "normalized_filename, file_path, checksum_sha256, status) "
                "VALUES (gen_random_uuid(), :fn, :norm, :fn, :cs, 'pending')"
            ),
            {"fn": f"test_{tag}.xlsx", "norm": f"t_{tag}_20260801_x.xlsx",
             "cs": f"test-{tag}"},
        )
    return tag


def _delete_by_checksum(tag: str) -> None:
    with get_session() as s:
        s.execute(
            text("DELETE FROM file_ingestion_meta WHERE checksum_sha256 = :cs"),
            {"cs": f"test-{tag}"},
        )


def test_claim_skips_locked_rows():
    from sqlalchemy.orm import Session as _Session

    from owl.load.database import get_engine

    _pg()
    engine = get_engine()
    r1 = _insert_pending("lock-a")
    r2 = _insert_pending("lock-b")
    try:
        holder = _Session(engine)
        try:
            # Lock r1's row in another transaction and hold it open.
            row = holder.execute(
                text("SELECT id FROM file_ingestion_meta "
                     "WHERE checksum_sha256 = :cs FOR UPDATE"),
                {"cs": f"test-{r1}"},
            ).first()
            assert row is not None
            claimer = _Session(engine)
            try:
                # Wide limit: our rows are newest; must appear despite older rows.
                claimed = claim_pending(claimer, limit=100)
                claimed_cs = {
                    claimer.execute(
                        text("SELECT checksum_sha256 FROM file_ingestion_meta WHERE id = :i"),
                        {"i": cid},
                    ).scalar()
                    for cid in claimed
                }
                assert f"test-{r1}" not in claimed_cs
                assert f"test-{r2}" in claimed_cs
            finally:
                claimer.rollback()
        finally:
            holder.rollback()
    finally:
        _delete_by_checksum(r1)
        _delete_by_checksum(r2)


def test_sweep_uses_updated_at_not_created_at():
    from api.main import _sweep_stuck_jobs

    _pg()
    tag = uuid.uuid4().hex[:6]
    old, new = _insert_pending(f"old-{tag}"), _insert_pending(f"new-{tag}")
    try:
        now = datetime.now(timezone.utc)
        with get_session() as s:
            # Old creation BUT freshly touched -> must survive.
            s.execute(
                text("UPDATE file_ingestion_meta SET status='processing', "
                     "created_at=:old, updated_at=:now "
                     "WHERE checksum_sha256=:cs"),
                {"old": now - timedelta(days=2), "now": now,
                 "cs": f"test-{old}"},
            )
            # Old and untouched -> recovered as failed.
            s.execute(
                text("UPDATE file_ingestion_meta SET status='processing', "
                     "created_at=:old, updated_at=:old "
                     "WHERE checksum_sha256=:cs"),
                {"old": now - timedelta(days=2), "cs": f"test-{new}"},
            )
        _sweep_stuck_jobs()
        with get_session() as s:
            states = dict(
                s.execute(
                    text("SELECT checksum_sha256, status FROM file_ingestion_meta "
                         "WHERE checksum_sha256 IN (:a, :b)"),
                    {"a": f"test-{old}", "b": f"test-{new}"},
                ).fetchall()
            )
        assert states[f"test-{old}"] == "processing"
        assert states[f"test-{new}"] == "failed"
    finally:
        _delete_by_checksum(old)
        _delete_by_checksum(new)
