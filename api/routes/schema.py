"""Database schema exposure (structure only — never row data).

Powers schema-aware UI (e.g. the Report Builder assistant's context strip):
table names with ordered columns (name, type, nullability) for the public
schema. Safe by construction: information_schema carries no table contents.
"""
from fastapi import APIRouter
from sqlalchemy import text

from owl.load.database import get_session

router = APIRouter(tags=["schema"])


@router.get("/schema")
def get_schema():
    with get_session() as s:
        rows = s.execute(
            text(
                "SELECT table_name, column_name, data_type, is_nullable "
                "FROM information_schema.columns "
                "WHERE table_schema = 'public' "
                "ORDER BY table_name, ordinal_position"
            )
        ).mappings().all()
    tables: dict[str, list[dict[str, object]]] = {}
    for r in rows:
        tables.setdefault(r["table_name"], []).append(
            {
                "name": r["column_name"],
                "type": r["data_type"],
                "nullable": r["is_nullable"] == "YES",
            }
        )
    return {
        "tables": [{"table": t, "columns": cols} for t, cols in tables.items()],
        "table_count": len(tables),
    }
