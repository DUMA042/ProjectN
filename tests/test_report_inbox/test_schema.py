"""Tests for the structure-only schema endpoint."""
from __future__ import annotations

from fastapi.testclient import TestClient

from api import main as app_module

client = TestClient(app_module.app)


def test_schema_shape_and_known_tables():
    res = client.get("/api/schema")
    assert res.status_code == 200
    body = res.json()
    assert body["table_count"] == len(body["tables"]) > 0
    by_name = {t["table"]: t["columns"] for t in body["tables"]}
    for expected in ("employees", "attendance_daily", "privacy_tokens"):
        assert expected in by_name, f"missing table {expected}"
    emp_cols = {c["name"] for c in by_name["employees"]}
    assert {"id_no", "full_name", "phone_number"} <= emp_cols
    for t in body["tables"]:
        for c in t["columns"]:
            assert set(c.keys()) == {"name", "type", "nullable"}
            assert isinstance(c["nullable"], bool)
