"""Defense-in-depth SQL security validator + read-only executor.

The compiler is trusted code, but this gate re-checks its output independently:
single statement, read-only leading keyword, no banned operations, every
identifier allowlisted, complexity caps. Then execution happens in a
read-only transaction with a statement timeout and a fetch cap.

Rationale: values can never smuggle syntax because the compiler binds every
value as a parameter — SQL text contains only compiler-emitted identifiers,
keywords, and constants. Anything else is rejected.
"""
from __future__ import annotations

import re

from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from owl.config import settings
from owl.load.database import get_session

STATEMENT_TIMEOUT = "15s"
MAX_FETCH_ROWS = 2000
MAX_JOINS = 4
MAX_PARAMS = 100
MAX_SQL_LEN = 20000

BANNED_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "MERGE", "UPSERT", "TRUNCATE", "DROP",
    "ALTER", "CREATE", "GRANT", "REVOKE", "COPY", "CALL", "COMMENT",
    "SECURITY", "VACUUM", "ANALYZE", "EXPLAIN", "EXECUTE", "SHOW", "SET",
    "RESET", "DISCARD", "LISTEN", "NOTIFY", "UNLISTEN", "CLUSTER", "REINDEX",
    "CHECKPOINT", "SAVEPOINT", "BEGIN", "COMMIT", "ROLLBACK", "START",
    "TRANSACTION", "LOCK", "ABORT", "PREPARE", "DEALLOCATE", "DO",
    "CONFLICT",
]
BANNED_RE = re.compile(r"\b(" + "|".join(BANNED_KEYWORDS) + r")\b", re.IGNORECASE)
IDENT_RE = re.compile(r'"([^"]+)"|:([A-Za-z_]\w*)|([A-Za-z_][\w$]*)')
DANGEROUS_FUNC_RE = re.compile(r"\b(pg_[A-Za-z_]+|dblink\w*|lo_import|lo_export|pg_read_file|pg_ls_dir|current_setting|version|md5|encode|decode|convert_from)\b", re.IGNORECASE)

# SQL vocabulary the compiler may legitimately emit.
KEYWORDS = {
    "SELECT", "DISTINCT", "FROM", "WHERE", "AND", "OR", "NOT", "IN", "BETWEEN",
    "LIKE", "ILIKE", "IS", "NULL", "GROUP", "BY", "HAVING", "ORDER", "ASC",
    "DESC", "LIMIT", "OFFSET", "AS", "LEFT", "INNER", "JOIN", "ON",
    "CASE", "WHEN", "THEN", "ELSE", "END",
    "COUNT", "SUM", "AVG", "MIN", "MAX",
    "ROUND", "COALESCE", "NULLIF", "EXTRACT", "YEAR", "MONTH", "EPOCH",
    "TRUE", "FALSE",
}


class SecurityError(ValueError):
    """Raised when generated SQL fails the security gate."""


def _strip_literals_comments(sql: str) -> str:
    """Return code regions only (quoted literals and comments removed)."""
    out = []
    i, n = 0, len(sql)
    while i < n:
        c = sql[i]
        if c == "'":
            i += 1
            while i < n:
                if sql[i] == "'" and i + 1 < n and sql[i + 1] == "'":
                    i += 2
                elif sql[i] == "'":
                    i += 1
                    break
                else:
                    i += 1
        elif c == "-" and i + 1 < n and sql[i + 1] == "-":
            while i < n and sql[i] != "\n":
                i += 1
        elif c == "/" and i + 1 < n and sql[i + 1] == "*":
            i += 2
            while i + 1 < n and not (sql[i] == "*" and sql[i + 1] == "/"):
                i += 1
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def validate_sql(sql: str, *, tables: set[str], columns: set[str], aliases: set[str]) -> None:
    """Independently vet compiler output. Raises SecurityError on any finding."""
    if not isinstance(sql, str) or not sql.strip():
        raise SecurityError("Empty SQL")
    if len(sql) > MAX_SQL_LEN:
        raise SecurityError("SQL too long")
    code = _strip_literals_comments(sql)
    if ";" in code:
        raise SecurityError("Multiple statements are not allowed")
    first = re.match(r"\s*(\w+)", code)
    if not first or first.group(1).upper() != "SELECT":
        raise SecurityError("Only SELECT statements are allowed")
    if BANNED_RE.search(code):
        raise SecurityError("Prohibited operation in SQL")
    if DANGEROUS_FUNC_RE.search(code):
        raise SecurityError("Dangerous function in SQL")
    if re.search(r"\$[A-Za-z_][\w$]*\$", code):
        raise SecurityError("Dollar-quoting is not allowed")

    allowed = set(KEYWORDS) | set(tables) | set(columns) | set(aliases)
    allowed_lower = {a.lower() for a in allowed}
    for m in IDENT_RE.finditer(code):
        if m.group(2) is not None:
            continue  # bound parameter placeholder (:p0) — values never inline
        name = m.group(1) if m.group(1) is not None else m.group(3)
        if name.lower() in allowed_lower:
            continue
        if name.isdigit():
            continue  # numeric literals
        raise SecurityError(f"Unapproved identifier '{name[:40]}'")

    if len(re.findall(r"\bJOIN\b", code, re.IGNORECASE)) > MAX_JOINS:
        raise SecurityError("Too many joins")


_reader_factory = None


@contextmanager
def reader_session():
    """Chatbot query session: dedicated read-only role when configured.

    With READER_DATABASE_URL set, connects as flow_reader (SELECT-only by
    grant). Otherwise falls back to the app session — still fenced by
    SET TRANSACTION READ ONLY + statement timeout + fetch cap below.
    """
    global _reader_factory
    url = (settings.reader_database_url or "").strip()
    if url:
        if _reader_factory is None:
            _reader_factory = sessionmaker(
                bind=create_engine(url, pool_pre_ping=True, pool_size=2, max_overflow=2),
                autocommit=False,
                autoflush=False,
            )
        session = _reader_factory()
        try:
            yield session
            session.rollback()
        finally:
            session.close()
    else:
        with get_session() as session:
            yield session


def run_validated(session, sql: str, params: dict, *, tables: set[str], columns: set[str], aliases: set[str], max_rows: int = MAX_FETCH_ROWS) -> dict:
    """Validate, then execute read-only with timeout + fetch cap.

    Returns {"columns": [...], "rows": [...], "row_count": n, "truncated": bool}.
    """
    validate_sql(sql, tables=tables, columns=columns, aliases=aliases)
    if len(params) > MAX_PARAMS:
        raise SecurityError("Too many parameters")
    # SET TRANSACTION must be the first statement of the transaction, but the
    # caller may already have autobegun one on this session (e.g. semantic
    # existence checks). Nothing is pending in this path, so close it first —
    # otherwise Postgres rejects the SET with ActiveSqlTransaction (25001).
    session.rollback()
    session.execute(text("SET TRANSACTION READ ONLY"))
    session.execute(text(f"SET LOCAL statement_timeout = '{STATEMENT_TIMEOUT}'"))
    result = session.execute(text(sql), params)
    columns_out = list(result.keys())
    fetched = result.mappings().fetchmany(max_rows + 1)
    rows = [dict(r) for r in fetched[:max_rows]]
    return {
        "columns": columns_out,
        "rows": rows,
        "row_count": len(rows),
        "truncated": len(fetched) > max_rows,
    }
