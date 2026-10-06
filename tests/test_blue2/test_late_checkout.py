"""Late checkout vs late arrival routing (no PII in asserts)."""
from __future__ import annotations

import json
from datetime import date

import httpx

from owl.ai import narrate, pipeline, router
from owl.load.database import get_session

TODAY = date(2026, 9, 30)


def _route(q):
    with get_session() as s:
        return router.route(q, s, {}, TODAY)


def _ir_fields(out):
    return [i.get("field") for i in out["ir"]["select"] if isinstance(i, dict)]


def _has_null_guard(out, field):
    def walk(node):
        if not isinstance(node, dict):
            return False
        if "and" in node or "or" in node:
            kids = node.get("and", node.get("or", [])) or []
            return any(walk(k) for k in kids)
        if "not" in node:
            return walk(node["not"])
        return node.get("field") == field and node.get("operator") == "IS NOT NULL"

    return walk(out["ir"]["filters"] or {})


def test_checkout_wording_routes_to_checkout_time():
    for q in (
        "find the list of top 5 late checkout",
        "who had the latest departures yesterday?",
        "top 3 late check-outs",
    ):
        out = _route(q)
        assert out is not None, q
        assert out["template"] == "late_checkouts", q
        assert "checkout_time" in _ir_fields(out), q
        assert "checkin_time" not in _ir_fields(out), q
        assert out["ir"]["order_by"] == [{"field": "checkout_time", "direction": "DESC"}]
        assert _has_null_guard(out, "checkout_time"), q


def test_arrival_wording_keeps_checkin_time():
    for q in (
        "top 5 latecomers",
        "who arrived late yesterday?",
        "who is late?",
    ):
        out = _route(q)
        assert out is not None, q
        assert out["template"] == "late_comers", q
        assert "checkin_time" in _ir_fields(out), q
        assert _has_null_guard(out, "checkin_time"), q


def test_early_branch_has_null_guard():
    out = _route("who checked in earliest yesterday?")
    assert out is not None
    assert out["template"] == "top_early"
    assert _has_null_guard(out, "checkin_time")


def test_late_checkouts_template():
    rows = [{"full_name": "[NAME-1]", "checkout_time": "18:42"}]
    text = narrate.render("late_checkouts", rows, None)
    assert text and "Latest checkouts" in text and "18:42" in text


def test_end_to_end_late_checkout_no_model_calls():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    transport = httpx.MockTransport(handler)
    with get_session() as s:
        out = pipeline.run_ask(s, "find the list of top 5 late checkout", transport=transport)
    assert calls == [], "router hit must not call the model"
    assert out["mode"] == "data"
    assert len(out["rows"]) == 5
    assert all(r.get("checkout_time") for r in out["rows"])
    assert "Latest checkouts" in out["answer"]
