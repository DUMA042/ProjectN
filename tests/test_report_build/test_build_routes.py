"""Build start/hash/status routes (tmp inbox + SQLite vault, no Postgres)."""
from __future__ import annotations

from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

import api.routes.report_build as build_routes
from api import main as app_module
from api.routes.report_inbox import save_manifest
from owl import config as config_module
from owl.reports import analysis as analysis_module

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

INDIVIDUAL = "full_name,idno,department\nAlice Ama,E001,HR\nBob Boateng,E002,IT\n"
PLAIN = "department,headcount\nHR,12\nIT,30\n"


@pytest.fixture()
def inbox(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module.settings, "report_inbox_dir", str(tmp_path))

    @contextmanager
    def fake_session():
        engine = create_engine("sqlite:///:memory:")
        with engine.connect() as conn:
            conn.execute(text(DDL))
            conn.commit()
        with Session(engine) as s:
            yield s
            s.commit()

    monkeypatch.setattr(build_routes, "get_session", fake_session)
    (tmp_path / "people.csv").write_text(INDIVIDUAL, encoding="utf-8")
    (tmp_path / "depts.csv").write_text(PLAIN, encoding="utf-8")
    save_manifest([
        {"id": "f1", "display_name": "people.csv", "stored_name": "people.csv",
         "source": "t", "row_count": 2, "byte_size": 10,
         "sent_at": "2026-01-01T00:00:00+00:00", "status": "build",
         "moved_at": None, "classification": "individual"},
        {"id": "f2", "display_name": "depts.csv", "stored_name": "depts.csv",
         "source": "t", "row_count": 2, "byte_size": 10,
         "sent_at": "2026-01-01T00:00:00+00:00", "status": "build",
         "moved_at": None, "classification": "non_individual"},
    ], tmp_path)
    return tmp_path


client = TestClient(app_module.app)


def test_start_detects_individual(inbox):
    res = client.post("/api/reports/build/start", json={"file_ids": ["f1", "f2"]})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["needs_hashing"] is True
    assert [f["id"] for f in body["individual_files"]] == ["f1"]
    assert "cannot perform" in body["hash_warning_names_and_ids"]
    st = client.get(f"/api/reports/build/jobs/{body['job_id']}")
    assert st.json()["stage"] == "inspected"


def test_start_rejects_empty_unknown_and_non_build(inbox):
    assert client.post("/api/reports/build/start", json={"file_ids": []}).status_code == 400
    assert client.post("/api/reports/build/start", json={"file_ids": ["nope"]}).status_code == 404


def test_hash_names_only_creates_copy_and_keeps_original(inbox):
    job_id = client.post("/api/reports/build/start", json={"file_ids": ["f1", "f2"]}).json()["job_id"]
    res = client.post(f"/api/reports/build/{job_id}/hash", json={"mode": "names_only"})
    assert res.status_code == 200, res.text
    assert res.json()["stage"] == "validated"
    # Original untouched; hashed copy exists with tokens.
    assert (inbox / "people.csv").read_text(encoding="utf-8") == INDIVIDUAL
    hashed = [p for p in inbox.glob("*_hashed*.csv")]
    assert len(hashed) == 1
    text = hashed[0].read_text(encoding="utf-8")
    assert "Alice Ama" not in text and "E001" in text
    st = client.get(f"/api/reports/build/jobs/{job_id}").json()
    assert st["stage"] == "validated"
    assert all(f["state"] == "done" for f in st["files"])


def test_hash_names_and_ids_and_bad_mode(inbox):
    job_id = client.post("/api/reports/build/start", json={"file_ids": ["f1"]}).json()["job_id"]
    res = client.post(f"/api/reports/build/{job_id}/hash", json={"mode": "names_and_ids"})
    assert res.status_code == 200, res.text
    hashed = [p for p in inbox.glob("*_hashed*.csv")]
    text = hashed[0].read_text(encoding="utf-8")
    assert "Alice Ama" not in text and "E001" not in text
    bad = client.post(f"/api/reports/build/{job_id}/hash", json={"mode": "everything"})
    assert bad.status_code == 400
    assert client.get("/api/reports/build/jobs/nope").status_code == 404


AI_REPLY = (
    '{"topics": [{"name": "Attendance", "coverage": "status column", '
    '"suggested_focus": "high"}], "recommended_range": '
    '{"min_words": 1000, "max_words": 1500, "reasoning": "two files"}}'
)


COMPREHENSION_REPLY = (
    '{"files": [{"name": "people.csv", "contains": "staff rows", '
    '"period": "June", "rows": 2}], "join_keys": [], '
    '"headline_figures": [], "caveats": []}'
)


def _dispatching_chat(monkeypatch, planner_reply):
    """Stub chat routing planner/comprehension calls to fitting payloads."""

    def fake_chat(messages, system=None, **kwargs):
        if system and "data analyst" in system:
            return COMPREHENSION_REPLY
        return planner_reply

    monkeypatch.setattr(analysis_module.deepseek, "chat", fake_chat)


def test_analyze_returns_topics_and_range(inbox, monkeypatch):
    _dispatching_chat(monkeypatch, AI_REPLY)
    job_id = client.post("/api/reports/build/start", json={"file_ids": ["f1", "f2"]}).json()["job_id"]
    client.post(f"/api/reports/build/{job_id}/hash", json={"mode": "names_only"})
    res = client.post(f"/api/reports/build/{job_id}/analyze")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["stage"] == "topics_ready"
    assert body["topics"][0]["name"] == "Attendance"
    assert body["recommended_range"]["max_words"] == 1500
    st = client.get(f"/api/reports/build/jobs/{job_id}").json()
    assert st["stage"] == "topics_ready"
    assert st["payload"]["topics"][0]["coverage"] == "status column"


def test_analyze_rejects_before_validation_and_bad_ai(inbox, monkeypatch):
    job_id = client.post("/api/reports/build/start", json={"file_ids": ["f1"]}).json()["job_id"]
    early = client.post(f"/api/reports/build/{job_id}/analyze")
    assert early.status_code == 400
    monkeypatch.setattr(analysis_module.deepseek, "chat", lambda *a, **k: "not json at all")
    client.post(f"/api/reports/build/{job_id}/hash", json={"mode": "names_only"})
    bad = client.post(f"/api/reports/build/{job_id}/analyze")
    assert bad.status_code == 502


def test_configure_stores_selection(inbox, monkeypatch):
    _dispatching_chat(monkeypatch, AI_REPLY)
    job_id = client.post("/api/reports/build/start", json={"file_ids": ["f1"]}).json()["job_id"]
    early = client.post(f"/api/reports/build/{job_id}/configure", json={
        "topics": [{"name": "Attendance", "include": True, "focus": "high"}],
        "word_range": {"min_words": 1000, "max_words": 1500},
    })
    assert early.status_code == 400
    client.post(f"/api/reports/build/{job_id}/hash", json={"mode": "names_only"})
    client.post(f"/api/reports/build/{job_id}/analyze")
    ok = client.post(f"/api/reports/build/{job_id}/configure", json={
        "topics": [{"name": "Attendance", "include": True, "focus": "high"}],
        "word_range": {"min_words": 1000, "max_words": 1500},
    })
    assert ok.status_code == 200, ok.text
    sel = ok.json()["selection"]
    assert sel["topics"] == [{"name": "Attendance", "include": True, "focus": "high"}]
    assert sel["word_range"] == {"min_words": 1000, "max_words": 1500}
    none = client.post(f"/api/reports/build/{job_id}/configure", json={
        "topics": [{"name": "Attendance", "include": False, "focus": "low"}],
        "word_range": {"min_words": 1000, "max_words": 1500},
    })
    assert none.status_code == 400
    unknown = client.post(f"/api/reports/build/{job_id}/configure", json={
        "topics": [{"name": "Nope", "include": True, "focus": "high"}],
        "word_range": {"min_words": 1000, "max_words": 1500},
    })
    assert unknown.status_code == 400


SECTION_REPLY = (
    "Rate was **83.3% (50 of 60 employees)**.\n\n"
    "- present: 50\n\n"
    "```charts\n"
    '[{"type": "bar", "title": "Presence", "labels": ["present", "absent"], "values": [50, 10]}]\n'
    "```"
)


def test_generate_builds_docx_and_preview(inbox, monkeypatch):
    from owl.reports import generate as gen_module

    COMPREHENSION = (
        '{"files": [{"name": "people.csv", "contains": "staff", '
        '"period": "June", "rows": 2}], "join_keys": [], '
        '"headline_figures": [], "caveats": []}'
    )

    def fake_chat(messages, system=None, **kwargs):
        # All AI stages share the deepseek module object; dispatch on system.
        if system and "report planner" in system:
            return AI_REPLY
        if system and "data analyst" in system:
            return COMPREHENSION
        return SECTION_REPLY

    monkeypatch.setattr(analysis_module.deepseek, "chat", fake_chat)
    assert gen_module.deepseek is analysis_module.deepseek
    job_id = client.post("/api/reports/build/start", json={"file_ids": ["f1", "f2"]}).json()["job_id"]
    early = client.post(f"/api/reports/build/{job_id}/generate")
    assert early.status_code == 400
    client.post(f"/api/reports/build/{job_id}/hash", json={"mode": "names_only"})
    client.post(f"/api/reports/build/{job_id}/analyze")
    client.post(f"/api/reports/build/{job_id}/configure", json={
        "topics": [{"name": "Attendance", "include": True, "focus": "high"}],
        "word_range": {"min_words": 500, "max_words": 1000},
    })
    res = client.post(f"/api/reports/build/{job_id}/generate")
    assert res.status_code == 200, res.text
    assert res.json()["stage"] == "complete"
    view = client.get(f"/api/reports/build/{job_id}/report")
    assert view.status_code == 200, view.text
    body = view.json()
    assert "83.3%" in body["markdown"]
    titles = [c["title"] for c in body["charts"]]
    # Backend-mandated visuals lead (department comparison guaranteed)…
    assert titles[0] == "Attendance by department"
    # …model-requested extras follow, deduped.
    assert "Presence" in titles
    assert len(titles) == len({t for t in titles})
    assert body["download_url"].endswith("/download")
    chart = client.get(body["charts"][0]["url"])
    assert chart.status_code == 200 and chart.headers["content-type"] == "image/png"
    dl = client.get(f"/api/reports/build/{job_id}/download")
    assert dl.status_code == 200
    assert "wordprocessingml" in dl.headers["content-type"]
    assert len(dl.content) > 8000
    assert "attachment" in dl.headers.get("content-disposition", "")
    assert "HR_Report_" in dl.headers.get("content-disposition", "")
    # Reconfiguring a completed job rolls back to topics_ready (rebuild path).
    again = client.post(f"/api/reports/build/{job_id}/configure", json={
        "topics": [{"name": "Attendance", "include": True, "focus": "high"}],
        "word_range": {"min_words": 500, "max_words": 1000},
    })
    assert again.status_code == 200, again.text
    assert again.json()["stage"] == "topics_ready"
    # Regenerating versions instead of overwriting: a second library entry.
    res2 = client.post(f"/api/reports/build/{job_id}/generate")
    assert res2.status_code == 200, res2.text
    lib = client.get("/api/reports/builds")
    assert lib.status_code == 200, lib.text
    reports = lib.json()["reports"]
    assert len(reports) == 2
    assert all(r["job_id"] == job_id for r in reports)
    assert reports[0]["topics"] == ["Attendance"]
    assert reports[0]["filename"].startswith("HR_Report_")
    assert reports[0]["download_url"].startswith("/api/reports/builds/")
    first, second = reports[1]["entry_id"], reports[0]["entry_id"]
    assert first != second
    for entry in (first, second):
        d = client.get(f"/api/reports/builds/{entry}/download")
        assert d.status_code == 200 and len(d.content) > 8000
    gone = client.delete(f"/api/reports/builds/{first}")
    assert gone.status_code == 200
    assert [r["entry_id"] for r in client.get("/api/reports/builds").json()["reports"]] == [second]
    assert client.delete(f"/api/reports/builds/{first}").status_code == 404


def test_rehash_replaces_in_place_and_never_doubles(inbox):
    job_id = client.post("/api/reports/build/start", json={"file_ids": ["f1"]}).json()["job_id"]
    client.post(f"/api/reports/build/{job_id}/hash", json={"mode": "names_only"})
    assert len([p for p in inbox.glob("*_hashed*.csv")]) == 1
    # Hashing again replaces the copy instead of adding another row/file.
    job2 = client.post("/api/reports/build/start", json={"file_ids": ["f1"]}).json()["job_id"]
    res = client.post(f"/api/reports/build/{job2}/hash", json={"mode": "names_and_ids"})
    assert res.status_code == 200, res.text
    assert len([p for p in inbox.glob("*_hashed*.csv")]) == 1
    from api.routes.report_inbox import load_manifest
    hashed_entries = [e for e in load_manifest(inbox) if str(e.get("source", "")).startswith("hashed:")]
    assert len(hashed_entries) == 1
    assert hashed_entries[0]["hash_mode"] == "names_and_ids"


def test_cancel_cleans_up_created_files(inbox):
    job_id = client.post("/api/reports/build/start", json={"file_ids": ["f1", "f2"]}).json()["job_id"]
    client.post(f"/api/reports/build/{job_id}/hash", json={"mode": "names_only"})
    assert len([p for p in inbox.glob("*_hashed*.csv")]) == 1
    res = client.post(f"/api/reports/build/{job_id}/cancel")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["cancelled"] is True and body["removed_hashed"] == 1
    assert [p for p in inbox.glob("*_hashed*.csv")] == []
    from api.routes.report_inbox import load_manifest
    assert all(not str(e.get("source", "")).startswith("hashed:") for e in load_manifest(inbox))
    # Originals untouched.
    assert (inbox / "people.csv").read_text(encoding="utf-8").startswith("full_name,idno")
    st = client.get(f"/api/reports/build/jobs/{job_id}").json()
    assert st["stage"] == "cancelled"
    # Cancelling again is idempotent (nothing left to clean).
    again = client.post(f"/api/reports/build/{job_id}/cancel")
    assert again.status_code == 200 and again.json()["removed_hashed"] == 0
    assert client.post("/api/reports/build/nope/cancel").status_code == 404
