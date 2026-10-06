"""DeepSeek chat client (OpenAI-compatible endpoint).

Security contract (do not weaken):
- The API key is read ONLY from ``owl.config.settings`` (operator's local
  ``.env``). It is never logged, never sent to the frontend, and never
  returned by any endpoint — only ever placed in the outbound Authorization
  header to api.deepseek.com.
- Fail closed: empty key raises ``NotConfigured`` (callers map it to a
  friendly "not configured" message).
- Error messages carry status codes only — never response bodies, never keys.
"""
from __future__ import annotations

import logging

import httpx

from owl.config import settings

BASE_URL = "https://api.deepseek.com"
# Planning prompts carry the full snapshot + rules, and Flash defaults to
# thinking mode — allow headroom so slow reasoning reads as patience, not failure.
TIMEOUT_SECONDS = 90.0
MAX_TURNS = 10
MAX_INPUT_CHARS = 6000
# Overload (503) retries: provider capacity errors are transient.
OVERLOAD_RETRIES = 2
OVERLOAD_BACKOFF_SECONDS = (2.0, 5.0)

log = logging.getLogger("owl.ai.deepseek")


class DeepSeekError(Exception):
    """Safe-to-display provider failure (never contains key material)."""


class NotConfigured(DeepSeekError):
    """Raised when no API key is configured."""


def _trim(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """Keep the tail of the conversation inside the char budget."""
    kept = [m for m in messages if m.get("content", "").strip()][-MAX_TURNS:]
    total = sum(len(m.get("content", "")) for m in kept)
    while kept and total > MAX_INPUT_CHARS:
        dropped = kept.pop(0)
        total -= len(dropped.get("content", ""))
    return kept


def chat(
    messages: list[dict[str, str]],
    *,
    system: str | None = None,
    transport: httpx.BaseTransport | None = None,
) -> str:
    """Send a chat conversation, return the reply text.

    ``messages``: [{"role": "user"|"assistant", "content": ...}].
    Raises NotConfigured (no key) or DeepSeekError (provider failure).
    """
    key = settings.deepseek_api_key.strip()
    if not key:
        raise NotConfigured(
            "AI is not configured. Add DEEPSEEK_API_KEY to your local .env and restart the API."
        )
    model = settings.deepseek_model.strip() or "deepseek-flash"
    payload_messages: list[dict[str, str]] = []
    if system and system.strip():
        payload_messages.append({"role": "system", "content": system.strip()})
    payload_messages.extend(_trim(messages))
    if not payload_messages or all(m["role"] != "user" for m in payload_messages):
        raise DeepSeekError("Nothing to send.")

    resp: httpx.Response | None = None
    try:
        with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT_SECONDS, transport=transport) as client:
            for attempt in range(OVERLOAD_RETRIES + 1):
                resp = client.post(
                    "/chat/completions",
                    headers={"Authorization": f"Bearer {key}"},
                    json={"model": model, "messages": payload_messages},
                )
                # Provider overloaded (transient capacity error): back off and
                # retry instead of surfacing it immediately.
                if resp.status_code != 503 or attempt >= OVERLOAD_RETRIES:
                    break
                log.warning("DeepSeek overloaded (attempt %s/%s)", attempt + 1, OVERLOAD_RETRIES + 1)
                if transport is None:
                    import time as _time

                    _time.sleep(OVERLOAD_BACKOFF_SECONDS[min(attempt, len(OVERLOAD_BACKOFF_SECONDS) - 1)])
    except httpx.TimeoutException:
        raise DeepSeekError("The AI took too long to respond. Please try again.")
    except httpx.HTTPError:
        log.warning("DeepSeek request failed (network)")
        raise DeepSeekError("Could not reach the AI service. Check your connection and try again.")
    assert resp is not None

    if resp.status_code == 401:
        raise DeepSeekError("The AI service rejected the credentials. Check DEEPSEEK_API_KEY and restart the API.")
    if resp.status_code == 429:
        raise DeepSeekError("The AI service is rate-limiting us. Wait a minute and try again.")
    if resp.status_code == 503:
        raise DeepSeekError("The backend is temporarily overloaded. Please retry.")
    if resp.status_code >= 400:
        log.warning("DeepSeek request failed (status=%s)", resp.status_code)
        raise DeepSeekError("The AI service returned an error. Please try again later.")
    try:
        data = resp.json()
        text = data["choices"][0]["message"]["content"] or ""
    except (ValueError, KeyError, IndexError, TypeError):
        raise DeepSeekError("The AI service returned an unreadable response. Please try again.")
    text = text.strip()
    if not text:
        raise DeepSeekError("The AI service returned an empty reply. Please try again.")
    return text
