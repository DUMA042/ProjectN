"""Settings endpoints — DB connection test, preferences."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, text

from owl.logger import get_logger

router = APIRouter(tags=["settings"])

log = get_logger(__name__)

# The prober exists to validate a *local* database setup. Restricting the
# target to loopback keeps it from being usable as a network reconnaissance
# tool (the API itself is loopback-bound, but defence in depth).
_ALLOWED_HOSTS = {"localhost", "127.0.0.1", "::1"}


class DBConnection(BaseModel):
    host: str = "localhost"
    port: int = 5433
    database: str = "flowdb"
    user: str = "postgres"
    password: str = ""


@router.post("/settings/test-db")
def test_db_connection(conn: DBConnection):
    if conn.host.strip().lower() not in _ALLOWED_HOSTS:
        raise HTTPException(
            status_code=400,
            detail="Only local database hosts (localhost, 127.0.0.1, ::1) can be tested.",
        )
    try:
        url = (
            f"postgresql+psycopg2://{conn.user}:{conn.password}"
            f"@{conn.host}:{conn.port}/{conn.database}"
        )
        engine = create_engine(url, connect_args={"connect_timeout": 5})
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        engine.dispose()
        return {"success": True, "message": "Database connection successful"}
    except Exception as exc:  # noqa: BLE001 — reported as a generic failure
        # Full detail (host, driver error) is logged only; the response must
        # not act as an infrastructure/credential oracle.
        log.warning("test-db failed for %s:%s/%s: %s: %s",
                    conn.host, conn.port, conn.database, type(exc).__name__, exc)
        return {
            "success": False,
            "message": "Could not connect to that database. Check the host, port, "
                       "database name, and credentials.",
        }
