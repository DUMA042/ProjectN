"""Tests for inbox Individual vs Non-individual classification."""
from __future__ import annotations

from api.routes.report_inbox import classify_csv


def test_id_headers_are_individual():
    assert classify_csv("id_no,full_name\n1,Ada\n") == "individual"
    assert classify_csv("ID No,Full Name\n1,Ada\n") == "individual"
    assert classify_csv("employee_id,employee\nE1,Ada\n") == "individual"
    assert classify_csv("Employee ID,Name\nE1,Ada\n") == "individual"
    assert classify_csv("  EMPLOYEE_ID ,x\nE1,1\n") == "individual"


def test_non_id_headers():
    assert classify_csv("full_name,department\nAda,HR\n") == "non_individual"
    assert classify_csv("metric,value\na,1\n") == "non_individual"
    # ID Hint is not a staff identifier.
    assert classify_csv("Employee Name,ID Hint\nAda,H1\n") == "non_individual"
    assert classify_csv("") == "non_individual"


def test_robust_headers():
    assert classify_csv("\ufeffid_no,name\n1,Ada\n") == "individual"
    assert classify_csv('"employee,id",name\nE1,Ada\n') == "non_individual"


def test_send_persists_classification():
    from fastapi.testclient import TestClient
    from api import main as app_module
    from owl import config as config_module
    import tempfile
    from pathlib import Path
    from unittest import mock

    with tempfile.TemporaryDirectory() as tmp:
        with mock.patch.object(config_module.settings, "report_inbox_dir", Path(tmp) / "inbox"):
            client = TestClient(app_module.app)
            res = client.post(
                "/api/reports/inbox",
                json={"filename": "r.csv", "source": "t", "csv_text": "id_no,name\n1,Ada\n"},
            )
            assert res.status_code == 200
            assert res.json()["classification"] == "individual"
            listed = client.get("/api/reports/inbox").json()["files"]
            assert listed[0]["classification"] == "individual"
