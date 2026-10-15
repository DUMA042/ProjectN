"""Malformed filter params are rejected (422), never silently ignored."""
from __future__ import annotations

from fastapi.testclient import TestClient

from api import main as app_module
from api.routes.params import parse_json_object_param

client = TestClient(app_module.app)


def test_parse_json_object_param():
    assert parse_json_object_param("") == {}
    assert parse_json_object_param(None) == {}
    assert parse_json_object_param('{"a": ["b"]}') == {"a": ["b"]}
    for bad in ("{oops", "[1, 2]", '"str"', "42"):
        try:
            parse_json_object_param(bad)
        except Exception as exc:  # noqa: BLE001 — asserting the status below
            assert getattr(exc, "status_code", None) == 422
        else:
            raise AssertionError(f"accepted {bad!r}")


def test_dashboard_rejects_bad_filters():
    res = client.get("/api/dashboard/employee-summary", params={"filters": "{oops"})
    assert res.status_code == 422


def test_analytics_rejects_bad_filters():
    res = client.get("/api/analytics/today", params={"filters": "[1]"})
    assert res.status_code == 422


def test_attendance_records_rejects_bad_filters():
    res = client.get("/api/employees/NOPE/attendance-records", params={"filters": "{oops"})
    assert res.status_code == 422
