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
import sys
from functools import lru_cache

from rich.logging import RichHandler

from owl.config import settings

_ROOT_LOGGER_NAME = "owl"
_CONFIGURED = False


def _configure_root_logger() -> None:
    """One-time setup of the root 'owl' logger.

    Called automatically the first time ``get_logger`` is invoked.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    root = logging.getLogger(_ROOT_LOGGER_NAME)
    root.setLevel(settings.log_level)

    # Avoid adding duplicate handlers if the function is somehow called twice.
    if not root.handlers:
        handler = RichHandler(
            level=settings.log_level,
            show_path=settings.environment == "development",
            rich_tracebacks=True,
            markup=True,
        )
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
