"""Vault-backed CSV hashing for the Build pipeline (SQLite-backed sessions)."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from owl.reports.hashing import detect_sensitive_columns, hash_csv_text

DDL = """
CREATE TABLE privacy_tokens (
    token CHAR(32) NOT NULL PRIMARY KEY,
    kind TEXT NOT NULL,
    norm TEXT NOT NULL,
    original TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (kind, norm)
)
"""

INDIVIDUAL_CSV = (
    "full_name,idno,department,days_present\n"
    "Alice Ama,E001,HR,20\n"
    "Bob Boateng,E002,IT,18\n"
    ",E003,IT,15\n"
)

PLAIN_CSV = "department,days_present\nHR,20\nIT,18\n"


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        conn.execute(text(DDL))
        conn.commit()
    with Session(engine) as s:
        yield s


def test_detect_name_and_id_columns():
    cols = detect_sensitive_columns(INDIVIDUAL_CSV)
    assert cols == {"name_idx": 0, "id_idx": 1}


def test_detect_ignores_lookalikes():
    # "department name" normalizes to "departmentname" — not the name column.
    cols = detect_sensitive_columns("department name,id_hint\nHR,x\n")
    assert cols == {"name_idx": None, "id_idx": None}


def test_names_only_keeps_ids(session):
    out, stats = hash_csv_text(session, INDIVIDUAL_CSV, "names_only")
    assert stats == {"names_hashed": 2, "ids_hashed": 0}
    lines = out.splitlines()
    assert lines[0] == "full_name,idno,department,days_present"
    assert "Alice Ama" not in out and "Bob Boateng" not in out
    assert "E001" in out and "E002" in out and "E003" in out
    # Blank name passes through; other cells untouched.
    assert lines[3].endswith(",E003,IT,15")
    # Same identity reuses one token (stable across files).
    again, _ = hash_csv_text(session, INDIVIDUAL_CSV, "names_only")
    assert again.splitlines()[1] == lines[1]


def test_names_and_ids_hashes_both(session):
    out, stats = hash_csv_text(session, INDIVIDUAL_CSV, "names_and_ids")
    assert stats == {"names_hashed": 2, "ids_hashed": 3}
    assert "Alice Ama" not in out and "E001" not in out


def test_missing_columns_rejected(session):
    with pytest.raises(ValueError, match="employee-name"):
        hash_csv_text(session, PLAIN_CSV, "names_only")
    with pytest.raises(ValueError, match="employee-ID"):
        hash_csv_text(session, "full_name,x\nA,1\n", "names_and_ids")
    with pytest.raises(ValueError, match="Unknown hash mode"):
        hash_csv_text(session, INDIVIDUAL_CSV, "everything")
