"""Settings endpoints — DB connection test, preferences."""
from fastapi import APIRouter
from pydantic import BaseModel
from owl.load.database import verify_connection

router = APIRouter(tags=["settings"])


class DBConnection(BaseModel):
    host: str = "localhost"
    port: int = 5433
    database: str = "flowdb"
    user: str = "postgres"
    password: str = ""


@router.post("/settings/test-db")
def test_db_connection(conn: DBConnection):
    try:
        url = f"postgresql+psycopg2://{conn.user}:{conn.password}@{conn.host}:{conn.port}/{conn.database}"
        from sqlalchemy import create_engine, text
        engine = create_engine(url, connect_args={"connect_timeout": 5})
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        engine.dispose()
        return {"success": True, "message": "Database connection successful"}
    except Exception as exc:
        return {"success": False, "message": str(exc)}
