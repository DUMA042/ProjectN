"""
owl.logger
~~~~~~~~~~
Structured, levelled logging for the entire owl pipeline.

Design decisions
----------------
* Uses Python's stdlib ``logging`` so any existing log handlers / aggregators
  (CloudWatch, Datadog, etc.) work without extra dependencies.
* ``rich.logging.RichHandler`` provides coloured, human-friendly output in
  development; in production (non-TTY) it degrades to plain text automatically.
* A single ``get_logger`` factory ensures every module gets a child logger
  under the ``owl`` namespace → all log records can be filtered or routed
  together in production.

Usage
-----
    from owl.logger import get_logger

    log = get_logger(__name__)
    log.info("Reading file", extra={"file": "attendance.xlsx"})
"""

import logging
import re
import sys
from functools import lru_cache

from rich.logging import RichHandler

from owl.config import settings

_ROOT_LOGGER_NAME = "owl"
_CONFIGURED = False
REDACTED = "***"

# PII shapes the pipeline logs in practice (e.g. "INSERT id_no=2029 name='X'").
# Redaction applies to rendered messages only; DEBUG stays verbatim so local
# debugging is unaffected.
_NAME_RE = re.compile(r"\b(full_name|employee_name|staff_name|name)\s*[=:]\s*'[^']*'", re.IGNORECASE)
_NAME_DQ_RE = re.compile(r'\b(full_name|employee_name|staff_name|name)\s*[=:]\s*"[^"]*"', re.IGNORECASE)
_ID_NO_RE = re.compile(
    r"\b(id_no|employee_id|staff_id|id_number)\s*[=:]\s*'?[^'\s,;)]+'?",
    re.IGNORECASE,
)
_SECRET_RE = re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b")


def redact_pii(text: str | None) -> str | None:
    """Mask employee identifiers, names, and API-key shapes (pure)."""
    if not text:
        return text
    text = _SECRET_RE.sub(f"sk-{REDACTED}", text)
    text = _NAME_RE.sub(lambda m: f"{m.group(1)}='{REDACTED}'", text)
    text = _NAME_DQ_RE.sub(lambda m: f'{m.group(1)}="{REDACTED}"', text)
    text = _ID_NO_RE.sub(lambda m: f"{m.group(1)}={REDACTED}", text)
    return text


class RedactionFilter(logging.Filter):
    """Redact PII from INFO and above; leave DEBUG records untouched."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003 — stdlib API
        if record.levelno < logging.INFO:
            return True
        try:
            message = record.getMessage()
        except Exception:  # noqa: BLE001 — never break logging
            return True
        redacted = redact_pii(message)
        if redacted != message:
            record.msg = redacted
            record.args = None
        return True


def _configure_root_logger() -> None:
    """One-time setup of the root 'owl' logger.

    Called automatically the first time ``get_logger`` is invoked.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    level = settings.effective_log_level
    root = logging.getLogger(_ROOT_LOGGER_NAME)
    root.setLevel(level)

    # Avoid adding duplicate handlers if the function is somehow called twice.
    if not root.handlers:
        handler = RichHandler(
            level=level,
            show_path=settings.environment == "development",
            rich_tracebacks=True,
            markup=True,
        )
        handler.addFilter(RedactionFilter())
        root.addHandler(handler)

    # Silence noisy third-party loggers unless we are in DEBUG mode.
    if settings.log_level != "DEBUG":
        for noisy in ("sqlalchemy.engine", "urllib3", "openpyxl"):
            logging.getLogger(noisy).setLevel(logging.WARNING)

    _CONFIGURED = True


@lru_cache(maxsize=None)
def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the 'owl' namespace.

    Parameters
    ----------
    name:
        Typically ``__name__`` of the calling module.

    Returns
    -------
    logging.Logger
        A configured child logger.

    Example
    -------
    >>> log = get_logger(__name__)
    >>> log.info("Pipeline started")
    """
    _configure_root_logger()

    # Ensure the name is scoped under the owl namespace.
    if not name.startswith(_ROOT_LOGGER_NAME):
        name = f"{_ROOT_LOGGER_NAME}.{name}"

    return logging.getLogger(name)
