"""Snapshot purity + drift tests (shape only — asserts carry no PII)."""
from __future__ import annotations

import json
import re

from owl.ai.snapshot import ALLOWED_TOP_KEYS, SNAPSHOT_PATH, live_columns, load

DIGIT_RUN = re.compile(r"\d{7,}")
FIXTURE_MARKERS = ("Testperson Alpha", "Testperson Beta")


def test_snapshot_shape_and_purity():
    snap = load()
    assert set(snap.keys()) <= ALLOWED_TOP_KEYS
    assert snap["tables"] and snap["rules"] and snap["intents"]
    blob = json.dumps(snap)
    assert not DIGIT_RUN.search(blob), "snapshot must not contain ID/phone-like digit runs"
    for marker in FIXTURE_MARKERS:
        assert marker not in blob
    assert "working_hours" in snap["rules"] and "holidays" in snap["rules"]


def test_snapshot_matches_live_shape():
    """Fail loudly on drift so regen+review happens (never silent wrong data)."""
    from owl.load.database import get_session

    snap = load()
    with get_session() as s:
        for table, cols in snap["tables"].items():
            assert live_columns(s, table) == cols, f"drift in {table}: regen snapshot"
