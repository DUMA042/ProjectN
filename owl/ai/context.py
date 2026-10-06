"""Prompt context builders (structure only — never row data)."""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def schema_summary(session: Session, max_tables: int = 60) -> str:
    """Compact 'table(col, col, ...)' listing for system prompts."""
    rows = session.execute(
        text(
            "SELECT table_name, string_agg(column_name, ', ' ORDER BY ordinal_position) AS cols "
            "FROM information_schema.columns "
            "WHERE table_schema = 'public' "
            "GROUP BY table_name ORDER BY table_name LIMIT :n"
        ),
        {"n": max_tables},
    ).mappings().all()
    parts = [f"{r['table_name']}({r['cols']})" for r in rows]
    return f"Database schema ({len(parts)} tables): " + " · ".join(parts)


SYSTEM_PREAMBLE = (
    "You are the assistant inside the Flow HR attendance application. "
    "You can see the database STRUCTURE (table and column names) but never any row data "
    "or personal details — say so plainly if asked for actual records. "
    "Answer concisely (a few sentences unless asked for detail). "
    "If a question needs data you cannot see, say which table/columns would answer it."
)
