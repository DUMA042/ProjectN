"""Assistant route tests: health shape + request validation (no AI calls)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from api import main as app_module

client = TestClient(app_module.app)


def test_health_reports_boolean_only():
    res = client.get("/api/assistant/health")
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body["configured"], bool)
    assert isinstance(body["model"], str)
    # The key must never appear in any response.
    assert "sk-" not in res.text


def test_chat_validation():
    assert client.post("/api/assistant/chat", json={"messages": []}).status_code == 400
    bad_role = {"messages": [{"role": "system", "content": "x"}]}
    assert client.post("/api/assistant/chat", json=bad_role).status_code == 400
    many = {"messages": [{"role": "user", "content": "x"}] * 25}
    assert client.post("/api/assistant/chat", json=many).status_code == 400
