"""FastAPI dependencies — DB session, settings."""

from typing import Generator

from sqlalchemy.orm import Session

from owl.load.database import get_db_session


def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session for use in route handlers."""
    with get_db_session() as session:
        yield session
