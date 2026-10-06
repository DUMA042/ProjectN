"""End-to-end pipeline tests: router fast path, routes, full data flow (no PII in asserts)."""
from __future__ import annotations

import json
import logging

import httpx

from owl.ai import pipeline
from owl.load.database import get_session


def _mock(*replies):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(json.loads(request.content.decode()))
        idx = min(len(calls) - 1, len(replies) - 1)
        body = replies[idx]
        if isinstance(body, Exception):
            raise body
        return httpx.Response(200, json={"choices": [{"message": {"content": body if isinstance(body, str) else json.dumps(body)}}]})

    return httpx.MockTransport(handler), calls


def test_router_fast_path_zero_model_calls():
    transport, calls = _mock()
    with get_session() as s:
        out = pipeline.run_ask(s, "who checked in earliest yesterday?", transport=transport)
    assert calls == [], "router hit must not call the model"
    assert out["mode"] == "data"
    assert out["row_count"] == len(out["rows"])
    assert out["columns"] and out["sql"].strip().lower().startswith("select")


def test_chat_and_clarify_routes():
    t1, _ = _mock({"route": "chat", "reply": "Hello there."})
    with get_session() as s:
        out = pipeline.run_ask(s, "hello?", transport=t1)
    assert out["mode"] == "general" and out["answer"] == "Hello there." and out["rows"] == []

    t2, _ = _mock({"route": "clarify", "question": "Which department did you mean?"})
    with get_session() as s:
        out = pipeline.run_ask(s, "show me stuff", transport=t2)
    assert out["mode"] == "clarify" and "department" in out["answer"]


def test_full_data_flow_with_mock_planner():
    ir = {"route": "query", "ir": {
        "source": "attendance",
        "select": [{"field": "department"},
                   {"aggregate": "COUNT", "field": "*", "alias": "n"}],
        "group_by": ["department"],
        "order_by": [{"field": "n", "direction": "DESC"}],
        "limit": 5,
    }}
    transport, calls = _mock(ir, "Summary: five departments listed.")
    with get_session() as s:
        out = pipeline.run_ask(s, "How many per department?", transport=transport)
    assert len(calls) == 2, "planner call + narration call"
    assert out["mode"] == "data"
    assert out["row_count"] > 0
    assert {c["name"] for c in out["columns"]} == {"department", "n"}
    assert isinstance(out["truncated"], bool)


def test_unsupported_and_invalid_shapes():
    t1, _ = _mock({"route": "unsupported"})
    with get_session() as s:
        out = pipeline.run_ask(s, "tell me a joke", transport=t1)
    assert out["mode"] == "unsupported" and out["rows"] == []

    t2, _ = _mock({"route": "query", "ir": {"source": "attendance", "select": [{"field": "password"}]}})
    with get_session() as s:
        out = pipeline.run_ask(s, "passwords please", transport=t2)
    assert out["mode"] == "unsupported"


def test_audit_is_metadata_only(caplog):
    t, _ = _mock({"route": "chat", "reply": "Hi."})
    with get_session() as s:
        with caplog.at_level(logging.INFO, logger="owl.ai.pipeline"):
            pipeline.run_ask(s, "Is Testperson Alpha on leave?", transport=t)
    assert "Testperson Alpha" not in caplog.text
    assert "blue_ask" in caplog.text


def test_blue_route_validation():
    from fastapi.testclient import TestClient

    from api import main as app_module

    client = TestClient(app_module.app)
    assert client.post("/api/blue/ask", json={"question": ""}).status_code == 400
    assert client.post("/api/blue/ask", json={"question": "x" * 2001}).status_code == 400


def test_destructive_intent_refused_without_model():
    import httpx as _hx

    from owl.ai import pipeline
    from owl.load.database import get_session

    def boom(request: _hx.Request) -> _hx.Response:
        raise AssertionError("model must not be consulted for destructive requests")

    transport = _hx.MockTransport(boom)
    with get_session() as s:
        for q in ("Delete employee 3555", "drop the attendance table", "truncate leave_records"):
            out = pipeline.run_ask(s, q, transport=transport)
            assert out["mode"] == "unsupported" and out["rows"] == []
            assert "read-only" in out["answer"].lower()
