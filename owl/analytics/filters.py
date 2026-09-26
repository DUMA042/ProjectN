"""Shared scope-filter builder for the Management analytics endpoints.

Builds a safe JOIN + WHERE fragment from a filters dict whose keys must come
from the whitelisted DIMENSIONS registry — same contract as the explore
engine, reused by today/signals/forecast so every endpoint honours the exact
page scope (location + dimension chips).
"""
from __future__ import annotations

from sqlalchemy import text

from owl.analytics.dimensions import DIMENSIONS, dimension_expr


def build_scope(filters: dict | None, params: dict, prefix: str = "f") -> tuple[str, str]:
    """Return (joins_sql, where_sql) for the given filter scope.

    ``params`` is populated with bound parameters; values never enter SQL text.
    """
    filters = filters or {}
    joins: list[str] = []
    seen: set[str] = set()
    clauses: list[str] = []
    i = 0
    for key, values in filters.items():
        if not values:
            continue
        meta = DIMENSIONS.get(key)
        if not meta:
            continue
        join = meta.get("join", "")
        if join and join not in seen:
            seen.add(join)
            joins.append(join)
        placeholders = []
        for v in values:
            pname = f"{prefix}{i}"
            params[pname] = v
            placeholders.append(f":{pname}")
            i += 1
        clauses.append(f"{meta['expr']} IN ({', '.join(placeholders)})")
    joins_sql = " ".join(joins)
    where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return joins_sql, where_sql


def scoped_count(session, base_table: str, filters: dict | None, extra_where: str = "") -> int:
    """COUNT(*) over a base table (aliased ``e``) with the scope filters applied."""
    params: dict = {}
    joins, where = build_scope(filters, params)
    sql = f"SELECT COUNT(*) FROM {base_table} e {joins} {where}"
    if extra_where:
        sql += (" AND " + extra_where) if where else ("WHERE " + extra_where)
    return session.execute(text(sql), params).scalar() or 0
