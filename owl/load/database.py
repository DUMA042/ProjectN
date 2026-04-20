"""
owl.load.database
~~~~~~~~~~~~~~~~~
SQLAlchemy engine and session factory.

Design decisions
----------------
* Engine creation is **lazy** — the engine is only built on the first call to
  ``get_engine()``.  This makes the module safely importable in test and
  CI environments where no database is configured.
* ``get_session()`` yields a session inside a context manager, guaranteeing
  clean rollback/close on exceptions.
* ``tenacity`` retry wraps the initial connection check so the pipeline can
  start before PostgreSQL is fully ready (useful in Docker / CI environments).
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from owl.config import settings
from owl.exceptions import LoadError
from owl.logger import get_logger

log = get_logger(__name__)

# ── Lazy engine singleton ──────────────────────────────────────────────────────
# Engine is built on first use so the module can be imported safely without
# a DATABASE_URL being configured (e.g. in test/CI environments).

_engine: Engine | None = None
_SessionFactory = None


def get_engine() -> Engine:
    """Return the SQLAlchemy engine, creating it on first call.

    Raises
    ------
    ValueError
        If DATABASE_URL has not been configured in .env.
    """
    global _engine, _SessionFactory
    if _engine is None:
        db_url = settings.get_database_url()   # raises ValueError if unset
        _engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            echo=(settings.log_level == "DEBUG"),
        )
        _SessionFactory = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
        log.debug("SQLAlchemy engine created.")
    return _engine


# ── Session context manager ────────────────────────────────────────────────────

@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Yield a transactional Session; roll back on error, close on exit.

    Usage
    -----
    >>> with get_session() as session:
    ...     session.add(record)
    """
    # Ensure engine (and _SessionFactory) are initialised.
    get_engine()

    session: Session = _SessionFactory()
    try:
        yield session
        session.commit()
    except Exception as exc:
        session.rollback()
        raise LoadError(
            "Database session error — transaction rolled back.",
            context={"original_error": str(exc)},
        ) from exc
    finally:
        session.close()


# ── Connection health check ────────────────────────────────────────────────────

@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
def verify_connection() -> None:
    """Check that the database is reachable; retry up to 5 times with backoff.

    Raises
    ------
    LoadError
        If the database cannot be reached after all retry attempts.
    """
    engine = get_engine()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        log.info("Database connection verified.")
    except Exception as exc:
        log.warning(f"Database connection failed: {exc}. Retrying…")
        raise
