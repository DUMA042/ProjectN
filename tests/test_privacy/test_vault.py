"""Unit tests for the reversible privacy token vault (SQLite-backed)."""
from __future__ import annotations

import re

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from owl.privacy.vault import (
    forget_tokens,
    get_or_create_tokens,
    normalize,
    resolve_tokens,
)

HEX32 = re.compile(r"^[0-9A-F]{32}$")

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


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        conn.execute(text(DDL))
        conn.commit()
    with Session(engine) as s:
        yield s


def test_token_shape_and_reuse(session):
    m1 = get_or_create_tokens(session, "name", ["Ada Brown"])
    assert HEX32.match(m1["Ada Brown"])
    m2 = get_or_create_tokens(session, "name", ["Ada Brown"])
    assert m2["Ada Brown"] == m1["Ada Brown"]


def test_normalization_dedupes(session):
    m = get_or_create_tokens(session, "name", ["  Ada   Brown ", "ada brown", "ADA BROWN"])
    assert len(set(m.values())) == 1


def test_namespaces_are_separate(session):
    m = get_or_create_tokens(session, "name", ["123"])
    i = get_or_create_tokens(session, "id", ["123"])
    assert m["123"] != i["123"]


def test_blanks_never_tokenized(session):
    m = get_or_create_tokens(session, "name", ["", "   ", "Ada Brown"])
    assert m[""] == "" and m["   "] == ""
    assert HEX32.match(m["Ada Brown"])
    count = session.execute(text("SELECT COUNT(*) FROM privacy_tokens")).scalar()
    assert count == 1


def test_unhash_roundtrip_and_unknown(session):
    m = get_or_create_tokens(session, "id", ["E001"])
    token = m["E001"]
    assert resolve_tokens(session, [token]) == {token: "E001"}
    assert resolve_tokens(session, ["0" * 32]) == {"0" * 32: None}
    assert resolve_tokens(session, [token.lower()]) == {token.lower(): "E001"}


def test_forget(session):
    m = get_or_create_tokens(session, "name", ["Ada Brown"])
    token = m["Ada Brown"]
    assert forget_tokens(session, [token]) == 1
    assert resolve_tokens(session, [token]) == {token: None}
    # Re-tokenizing after forget mints a (possibly new) token again.
    m2 = get_or_create_tokens(session, "name", ["Ada Brown"])
    assert HEX32.match(m2["Ada Brown"])


def test_validation(session):
    with pytest.raises(ValueError):
        get_or_create_tokens(session, "nickname", ["Ada"])
    with pytest.raises(ValueError):
        get_or_create_tokens(session, "name", ["x"] * 5001)


def test_normalize():
    assert normalize("  Ada   Brown ") == "ada brown"
