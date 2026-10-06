"""Unit tests for the DeepSeek client (mock transport — no key, no network)."""
from __future__ import annotations

import json

import httpx
import pytest

from owl import config as config_module
from owl.ai import deepseek


def _transport(status=200, payload=None, exc=None):
    def handler(request: httpx.Request) -> httpx.Response:
        # The key must travel ONLY in the Authorization header.
        assert request.headers.get("Authorization", "").startswith("Bearer ")
        if exc:
            raise exc
        return httpx.Response(status, json=payload if payload is not None else {})

    return httpx.MockTransport(handler)


@pytest.fixture()
def keyed(monkeypatch):
    monkeypatch.setattr(config_module.settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr(config_module.settings, "deepseek_model", "deepseek-flash")


def ok_payload(text="Hello"):
    return {"choices": [{"message": {"content": text}}]}


def test_success(keyed):
    t = _transport(200, ok_payload("Hi there"))
    assert deepseek.chat([{"role": "user", "content": "hi"}], transport=t) == "Hi there"


def test_not_configured(monkeypatch):
    monkeypatch.setattr(config_module.settings, "deepseek_api_key", "   ")
    with pytest.raises(deepseek.NotConfigured):
        deepseek.chat([{"role": "user", "content": "hi"}])


def test_auth_rejected(keyed):
    with pytest.raises(deepseek.DeepSeekError, match="credentials"):
        deepseek.chat([{"role": "user", "content": "hi"}], transport=_transport(401, {}))


def test_rate_limited(keyed):
    with pytest.raises(deepseek.DeepSeekError, match="rate"):
        deepseek.chat([{"role": "user", "content": "hi"}], transport=_transport(429, {}))


def test_timeout(keyed):
    with pytest.raises(deepseek.DeepSeekError, match="too long"):
        deepseek.chat(
            [{"role": "user", "content": "hi"}],
            transport=_transport(exc=httpx.TimeoutException("slow")),
        )


def test_bad_payload(keyed):
    with pytest.raises(deepseek.DeepSeekError, match="unreadable"):
        deepseek.chat([{"role": "user", "content": "hi"}], transport=_transport(200, {"nope": 1}))


def test_overload_retries_then_succeeds(keyed):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) < 3:
            return httpx.Response(503, json={"error": {"message": "overloaded"}})
        return httpx.Response(200, json=ok_payload("recovered"))

    assert deepseek.chat([{"role": "user", "content": "hi"}], transport=httpx.MockTransport(handler)) == "recovered"
    assert len(calls) == 3
    assert all(json.loads(c.content.decode())["model"] == "deepseek-flash" for c in calls)


def test_overload_exhausted(keyed):
    with pytest.raises(deepseek.DeepSeekError, match="temporarily overloaded"):
        deepseek.chat([{"role": "user", "content": "hi"}], transport=_transport(503, {}))


def test_history_trimmed(keyed):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content.decode())
        return httpx.Response(200, json=ok_payload())

    msgs = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}"} for i in range(30)]
    deepseek.chat(msgs, transport=httpx.MockTransport(handler))
    sent = seen["body"]["messages"]
    assert len(sent) <= deepseek.MAX_TURNS
    assert sent[-1]["content"] == "m29"
