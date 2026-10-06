"""Individual-report routes (tmp dirs + stubbed roster, real docx render)."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

import api.routes.individual_reports as routes
from api import main as app_module
from owl import config as config_module
from owl.reports.individual import ReportContext

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

EMP = {"id_no": "E1", "full_name": "Alice Ama", "sex": "F", "department": "HR",
       "grade_level": "5", "rank": "R", "employment_status": "Active", "location": "HQ"}


@pytest.fixture()
def env(tmp_path, monkeypatch):
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

    monkeypatch.setattr(routes, "get_session", fake_session)

    def fake_roster(session, location="", departments=None, employee_ids=None, search=""):
        return [dict(EMP)]

    def fake_days(session, ids, sd, ed):
        from datetime import datetime

        def dt(hm):
            return datetime(2026, 8, 3, int(hm[:2]), int(hm[3:5]))

        return {"E1": {"swipes": {date(2026, 8, 3): (dt("07:50"), dt("17:10"))},
                       "leaves": [], "trainings": []}}

    def fake_ctx():
        return ReportContext({}, set(), ["Active"], 1, [0, 1, 2, 3, 4], True,
                             date(2026, 8, 31))

    monkeypatch.setattr(routes.ind, "resolve_roster", fake_roster)
    monkeypatch.setattr(routes.ind, "load_day_data", fake_days)
    monkeypatch.setattr(routes.ind, "load_context", fake_ctx)
    return tmp_path


client = TestClient(app_module.app)
BODY = {"location": "HQ", "departments": [], "employee_ids": [],
        "start_date": "2026-08-03", "end_date": "2026-08-07"}


def test_validation(env):
    bad = dict(BODY, start_date="08/03/2026")
    assert client.post("/api/individual-reports/build", json=bad).status_code == 422
    flipped = dict(BODY, start_date="2026-08-07", end_date="2026-08-03")
    assert client.post("/api/individual-reports/build", json=flipped).status_code == 422
    wide = dict(BODY, start_date="2026-01-01", end_date="2026-12-31")
    assert client.post("/api/individual-reports/build", json=wide).status_code == 422


def _wait_complete(job_id, timeout_s=60):
    import time

    from owl.reports import jobs as _jobs

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        job = _jobs.get_job(job_id)
        assert job is not None
        if job["stage"] in ("complete", "failed", "cancelled"):
            return job
        time.sleep(0.2)
    raise AssertionError("individual build did not finish in time")


def test_full_build_and_library(env):
    res = client.post("/api/individual-reports/build", json=BODY)
    assert res.status_code == 200, res.text
    job_id = res.json()["job_id"]
    job = _wait_complete(job_id)
    assert job["stage"] == "complete", job
    result = job["payload"]["result"]
    assert result["headcount"] == 1
    lib = client.get("/api/individual-reports").json()["reports"]
    assert len(lib) == 1
    assert lib[0]["headcount"] == 1 and lib[0]["location"] == "HQ"
    assert lib[0]["filename"].endswith(".docx")
    dl = client.get(result["download_url"])
    assert dl.status_code == 200 and len(dl.content) > 5000
    assert client.delete(f"/api/individual-reports/{job_id}").status_code == 200
    assert client.get("/api/individual-reports").json()["reports"] == []


def test_missing_entries_404(env):
    assert client.get("/api/individual-reports/nope/download").status_code == 404
    assert client.delete("/api/individual-reports/nope").status_code == 404
    assert client.post("/api/individual-reports/nope/cancel").status_code == 404


def test_real_names_rendered_ids_intact(env):
    # No vault involved: processed data never leaves the system, so the
    # document carries real names (hashing was removed from this flow).
    job_id = client.post("/api/individual-reports/build", json=BODY).json()["job_id"]
    job = _wait_complete(job_id)
    assert job["stage"] == "complete", job
    assert all(f["state"] == "done" for f in job["files"])
    from docx import Document as _Doc

    docx = next((env / "individual").rglob("*.docx"))
    doc = _Doc(str(docx))
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "Alice Ama" in text  # real name rendered
    assert "E1" in text  # IDs intact


def test_weekend_only_range_fails_cleanly(env, monkeypatch):
    from owl.reports.individual import ReportContext as _RC

    monkeypatch.setattr(
        routes.ind, "load_context",
        lambda: _RC({}, set(), ["Active"], 1, [1, 2, 3, 4, 5], True, date(2026, 8, 31)),
    )
    weekend = dict(BODY, start_date="2026-08-08", end_date="2026-08-09")
    job_id = client.post("/api/individual-reports/build", json=weekend).json()["job_id"]
    job = _wait_complete(job_id)
    assert job["stage"] == "failed"
    assert "No workdays" in job["stage_detail"]
