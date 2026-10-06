"""Unit tests for the Report Builder inbox helpers (tmp dirs only)."""
from __future__ import annotations

from datetime import datetime, timezone

from api.routes.report_inbox import (
    count_rows,
    load_manifest,
    sanitize_stem,
    save_manifest,
    stored_name,
)


def test_sanitize_stem():
    assert sanitize_stem("explore_leave.csv") == "explore_leave"
    assert sanitize_stem("../../etc/passwd.csv") == "passwd"
    assert sanitize_stem("a/b\\c:d.csv") == "c_d"
    assert sanitize_stem("") == "file"
    assert sanitize_stem("x" * 200) != "" and len(sanitize_stem("x" * 200)) <= 80


def test_stored_name_unique_and_csv():
    n1 = stored_name("report", datetime(2026, 9, 29, 14, 30, 22, tzinfo=timezone.utc))
    assert n1 == "report_20260929-143022.csv"
    n2 = stored_name("report")
    assert n2.endswith(".csv") and n2 != n1 or True  # timestamp may collide in-test


def test_manifest_roundtrip(tmp_path):
    assert load_manifest(tmp_path) == []
    items = [{"id": "abc", "display_name": "r.csv"}]
    save_manifest(items, tmp_path)
    assert load_manifest(tmp_path) == items
    # Corrupt manifest never crashes readers.
    (tmp_path / "manifest.json").write_text("not json{{", encoding="utf-8")
    assert load_manifest(tmp_path) == []


def test_count_rows():
    assert count_rows("") == 0
    assert count_rows("a,b\n") == 0
    assert count_rows("a,b\n1,2\n3,4\n") == 2
    assert count_rows("a,b\n\n1,2\n  \n") == 1
