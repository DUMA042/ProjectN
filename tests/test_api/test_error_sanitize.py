"""Response sanitisation, prober guard, CORS, and docs exposure."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api import main as app_module
from api.routes.errors import MAX_SAFE_LENGTH, safe_error_detail
from owl.config import settings


def test_authored_validation_message_passes_through():
    msg = safe_error_detail(ValueError("start_date must be <= end_date"), "fallback")
    assert msg == "start_date must be <= end_date"


@pytest.mark.parametrize("leaky", [
    'relation "employees" does not exist\nLINE 1: SELECT ...',
    "connection to server at 127.0.0.1 failed: password authentication failed",
    "psycopg2.OperationalError: could not connect",
    'Traceback (most recent call last):\n  File "x.py"',
    "postgresql+psycopg2://user:secret@localhost/db",
    r"C:\Users\HP\data\report.xlsx is not readable",
    "using key sk-abcdef1234567890",
])
def test_internal_detail_is_replaced(leaky):
    msg = safe_error_detail(RuntimeError(leaky), "Could not do the thing.")
    assert msg == "Could not do the thing."
    assert "psycopg2" not in msg and "sk-" not in msg


def test_long_detail_is_replaced():
    assert safe_error_detail(RuntimeError("x" * (MAX_SAFE_LENGTH + 1)), "fallback") == "fallback"


client = TestClient(app_module.app)


def test_test_db_rejects_non_loopback_hosts():
    res = client.post("/api/settings/test-db", json={"host": "10.0.0.5"})
    assert res.status_code == 400
    assert "local database hosts" in res.json()["detail"]


def test_cors_allows_configured_origin_only():
    allowed = settings.cors_origins[0]
    ok = client.get("/api/health", headers={"Origin": allowed})
    assert ok.headers.get("access-control-allow-origin") == allowed

    bad = client.get("/api/health", headers={"Origin": "http://evil.example"})
    assert bad.headers.get("access-control-allow-origin") is None


def test_cors_does_not_allow_credentials():
    allowed = settings.cors_origins[0]
    res = client.get("/api/health", headers={"Origin": allowed})
    assert res.headers.get("access-control-allow-credentials") != "true"


def test_docs_exposure_follows_environment():
    assert (app_module.app.docs_url == "/docs") is settings.docs_enabled
    assert (app_module.app.openapi_url == "/openapi.json") is settings.docs_enabled
