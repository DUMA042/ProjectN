"""Safe error details for HTTP responses.

Authored validation messages ("start_date must be <= end_date") are useful to
the caller and are passed through. Anything that looks like infrastructure —
SQL text, driver errors, filesystem paths, credentials, provider bodies — is
replaced by a caller-supplied fallback, with the full detail written to the
log instead. Status codes never change.
"""
from __future__ import annotations

from owl.logger import get_logger

log = get_logger(__name__)

MAX_SAFE_LENGTH = 300

_INTERNAL_MARKERS = (
    "traceback",
    'file "',
    "psycopg2",
    "sqlalchemy",
    " select ",
    " insert into ",
    " delete from ",
    " update ",
    "postgresql",
    "password authentication",
    "connection to server",
    "could not connect",
    "no such file or directory",
    "winerror",
    "c:\\",
    "/usr/",
    "/home/",
    "/var/",
    "sk-",
)


def safe_error_detail(exc: BaseException, fallback: str, *, context: str = "") -> str:
    """Return a caller-safe message for *exc*; log the real error.

    The full exception is always logged (server-side only). The returned
    string is either the authored message or *fallback*.
    """
    log.warning(
        "request error%s: %s: %s",
        f" ({context})" if context else "",
        type(exc).__name__,
        exc,
    )
    text = str(exc).strip()
    if not text or len(text) > MAX_SAFE_LENGTH:
        return fallback
    lowered = text.lower()
    if any(marker in lowered for marker in _INTERNAL_MARKERS):
        return fallback
    return text
