"""Endpoint tests for inbox move (tmp inbox dir, no real files touched)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api import main as app_module
from owl import config as config_module


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module.settings, "report_inbox_dir", tmp_path / "inbox")
    return TestClient(app_module.app)


def _send(client, filename="r.csv"):
    res = client.post(
        "/api/reports/inbox",
        json={"filename": filename, "source": "test", "csv_text": "a,b\n1,2\n"},
    )
    assert res.status_code == 200
    return res.json()


def test_move_round_trip(client):
    entry = _send(client)
    assert entry["status"] == "inbox"
    assert entry["moved_at"] is None

    moved = client.post(f"/api/reports/inbox/{entry['id']}/move", json={"status": "build"})
    assert moved.status_code == 200
    assert moved.json()["status"] == "build"
    assert moved.json()["moved_at"]

    back = client.post(f"/api/reports/inbox/{entry['id']}/move", json={"status": "inbox"})
    assert back.json()["status"] == "inbox"

    listed = client.get("/api/reports/inbox").json()["files"]
    assert listed[0]["status"] == "inbox"


def test_move_validation(client):
    entry = _send(client)
    bad = client.post(f"/api/reports/inbox/{entry['id']}/move", json={"status": "archive"})
    assert bad.status_code == 400
    missing = client.post("/api/reports/inbox/nope/move", json={"status": "build"})
    assert missing.status_code == 404


def test_legacy_entry_without_status(client, tmp_path, monkeypatch):
    import json

    monkeypatch.setattr(config_module.settings, "report_inbox_dir", tmp_path / "inbox2")
    base = tmp_path / "inbox2"
    base.mkdir(parents=True, exist_ok=True)
    (base / "old.csv").write_text("a\n1\n", encoding="utf-8")
    (base / "manifest.json").write_text(
        json.dumps([{"id": "old1", "display_name": "old.csv", "stored_name": "old.csv"}]),
        encoding="utf-8",
    )
    # Legacy row lists fine and can be moved (treated as inbox).
    assert client.get("/api/reports/inbox").json()["files"][0]["id"] == "old1"
    moved = client.post("/api/reports/inbox/old1/move", json={"status": "build"})
    assert moved.status_code == 200
    assert moved.json()["status"] == "build"
    # Download still works for legacy rows.
    dl = client.get("/api/reports/inbox/old1/download")
    assert dl.status_code == 200
