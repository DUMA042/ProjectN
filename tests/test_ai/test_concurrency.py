"""AI call concurrency is bounded by the process-wide semaphore."""
from __future__ import annotations

import threading
import time

import httpx
import pytest

from owl import config as config_module
from owl.ai import deepseek


@pytest.fixture()
def keyed(monkeypatch):
    monkeypatch.setattr(config_module.settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr(config_module.settings, "deepseek_model", "deepseek-flash")


class CountingTransport(httpx.BaseTransport):
    """Blocks long enough for concurrent callers to overlap, then answers."""

    def __init__(self, delay: float = 0.15) -> None:
        self.delay = delay
        self.in_flight = 0
        self.max_in_flight = 0
        self._lock = threading.Lock()

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        with self._lock:
            self.in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self.in_flight)
        time.sleep(self.delay)
        with self._lock:
            self.in_flight -= 1
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok"}}]},
            request=request,
        )


def _run(transport, results, index):
    try:
        deepseek.chat([{"role": "user", "content": "hi"}], transport=transport)
        results[index] = "ok"
    except Exception as exc:  # noqa: BLE001
        results[index] = type(exc).__name__


def test_never_exceeds_configured_concurrency(keyed, monkeypatch):
    transport = CountingTransport()
    # Fresh semaphore so the test is independent of import-time state.
    monkeypatch.setattr(deepseek, "_call_slots", threading.BoundedSemaphore(2))
    results: list[str | None] = [None] * 6

    threads = [threading.Thread(target=_run, args=(transport, results, i)) for i in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert results == ["ok"] * 6
    assert transport.max_in_flight <= 2, transport.max_in_flight
    assert transport.max_in_flight >= 2, "calls should be able to run in parallel"


def test_slot_is_released_after_provider_error(keyed, monkeypatch):
    monkeypatch.setattr(deepseek, "_call_slots", threading.BoundedSemaphore(1))

    class Failing(httpx.BaseTransport):
        def handle_request(self, request):
            raise httpx.ConnectError("down", request=request)

    with pytest.raises(deepseek.DeepSeekError):
        deepseek.chat([{"role": "user", "content": "hi"}], transport=Failing())

    # A subsequent call must still be able to acquire the single slot.
    transport = CountingTransport(delay=0.01)
    assert deepseek.chat([{"role": "user", "content": "hi"}], transport=transport) == "ok"
