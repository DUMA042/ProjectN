"""Ingestion tests touch the local database.

Every synthetic row is identifiable by a ``test-`` checksum prefix. This
fixture removes them before and after each test so a failing test can never
leave rows behind that the next run would claim and try to process.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from owl.load.database import get_session

TEST_CHECKSUM_PREFIX = "test-"


def _purge_test_rows() -> None:
    try:
        with get_session() as s:
            s.execute(
                text("DELETE FROM file_ingestion_meta WHERE checksum_sha256 LIKE :p"),
                {"p": f"{TEST_CHECKSUM_PREFIX}%"},
            )
    except Exception:  # noqa: BLE001 — database may be unavailable (tests skip)
        pass


@pytest.fixture(autouse=True)
def clean_synthetic_ingest_rows():
    _purge_test_rows()
    yield
    _purge_test_rows()
