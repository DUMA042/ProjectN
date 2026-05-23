"""
owl.load.loader
~~~~~~~~~~~~~~~
Orchestrates bulk upsert / insert of normalised entity DataFrames to PostgreSQL.

Design
------
* ``DataLoader`` accepts a ``NormalizedEntities`` dict (output of the normalizer)
  and persists each entity DataFrame to its corresponding table.
* Uses PostgreSQL ``ON CONFLICT DO UPDATE`` for idempotent upserts.
* Supports "Robust" loading mode which isolates bad rows rather than failing the batch.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from owl.exceptions import LoadError
from owl.load.models import Base
from owl.logger import get_logger

log = get_logger(__name__)


@dataclass
class EntityLoadReport:
    """Detailed report of a single table's load result."""
    table_name: str
    success_count: int = 0
    failed_rows: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _build_model_map() -> dict[str, type]:
    """Lazily build a {table_name: ORM class} map from the declarative registry."""
    return {
        mapper.persist_selectable.name: mapper.class_
        for mapper in Base.registry.mappers
    }


class DataLoader:
    """Persist normalised entity DataFrames to PostgreSQL.

    Parameters
    ----------
    session:
        An active SQLAlchemy ``Session``.
    robust:
        If True, isolates bad rows by falling back to row-by-row insertion on failure.
    """

    def __init__(self, session: Session, robust: bool = True) -> None:
        self._session = session
        self._robust = robust
        self._model_map = _build_model_map()

    def load(self, entities: dict[str, pd.DataFrame]) -> dict[str, EntityLoadReport]:
        """Persist all entities. Returns mapping of table name to load report."""
        reports: dict[str, EntityLoadReport] = {}
        for table_name, df in entities.items():
            report = self._upsert_entity(table_name, df)
            reports[table_name] = report
            log.info(f"Load complete for '{table_name}': {report.success_count} success, {len(report.failed_rows)} failed.")
        return reports

    def _upsert_entity(self, table_name: str, df: pd.DataFrame) -> EntityLoadReport:
        """Upsert a single entity DataFrame into *table_name*."""
        report = EntityLoadReport(table_name=table_name)
        
        if df.empty:
            return report

        model_class = self._model_map.get(table_name)
        if model_class is None:
            raise LoadError(f"No ORM model registered for table '{table_name}'.")

        records = df.to_dict(orient="records")
        table = model_class.__table__
        pk_cols = [col.name for col in table.primary_key.columns]

        # Remove PKs that are None across all records to allow auto-increment
        for pk in pk_cols:
            if all(r.get(pk) is None for r in records):
                for r in records:
                    r.pop(pk, None)

        # 1. Attempt Bulk Operation
        try:
            self._execute_upsert(table, pk_cols, records)
            report.success_count = len(records)
            return report
        except Exception as exc:
            if not self._robust:
                raise LoadError(f"Bulk load failed for '{table_name}'.", context={"error": str(exc)})
            
            log.warning(f"Bulk load failed for '{table_name}'. Falling back to row-by-row recovery. Error: {exc}")
            self._session.rollback() # Clear the failed transaction state if necessary (handled by get_session usually, but be safe)

        # 2. Robust Recovery: Row-by-row isolation
        for record in records:
            try:
                # We use a nested transaction (savepoint) for each row in robust mode
                with self._session.begin_nested():
                    self._execute_upsert(table, pk_cols, [record])
                report.success_count += 1
            except Exception as exc:
                report.failed_rows.append(record)
                report.errors.append(str(exc))
                log.error(f"Row failed in '{table_name}': {exc}")

        return report

    def _execute_upsert(self, table, pk_cols: list[str], records: list[dict]) -> None:
        """Helper to execute a PG upsert statement."""
        stmt = pg_insert(table).values(records)
        update_cols = {
            col.name: stmt.excluded[col.name]
            for col in table.columns
            if col.name not in pk_cols
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=pk_cols,
            set_=update_cols,
        )
        self._session.execute(stmt)
        # We don't commit here; commit is handled by the caller/pipeline session context.
