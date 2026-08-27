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


# ── Deduplication registry ────────────────────────────────────────────────────
# Tables whose business columns form a natural unique key. When a table is
# present here, inserts use ON CONFLICT DO NOTHING against these columns
# (backed by a matching unique index in the database) instead of the default
# primary-key upsert — preventing duplicate rows when the same file content
# is processed again.
DEDUP_CONFLICT_COLUMNS: dict[str, list[str]] = {
    "employee_trainings": ["id_no", "venue_id", "consultant_id", "start_date", "end_date"],
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
        """Upsert a single entity DataFrame into *table_name*.

        Implements 3-tier fallback:
          1. Bulk insert                  (fast, single round-trip)
          2. Batch-of-50 with savepoints   (medium, ~2% of row-by-row round-trips)
          3. Batch-of-10 with savepoints   (fine-grained retry)
          4. Row-by-row with savepoints    (last resort, isolates single bad rows)
        """
        report = EntityLoadReport(table_name=table_name)

        if df.empty:
            return report

        model_class = self._model_map.get(table_name)
        if model_class is None:
            raise LoadError(f"No ORM model registered for table '{table_name}'.")

        records = df.to_dict(orient="records")
        table = model_class.__table__
        pk_cols = [col.name for col in table.primary_key.columns]

        for pk in pk_cols:
            if all(r.get(pk) is None for r in records):
                for r in records:
                    r.pop(pk, None)

        total = len(records)

        # ── Tier 1: Bulk insert ────────────────────────────────────────────
        try:
            self._execute_upsert(table, pk_cols, records)
            report.success_count = total
            return report
        except Exception as exc:
            if not self._robust:
                raise LoadError(f"Bulk load failed for '{table_name}'.", context={"error": str(exc)})
            log.warning(f"Bulk load failed for '{table_name}' ({total} rows). Falling back to batched recovery.")

        # ── Tier 2 & 3 & 4: Batched recovery ────────────────────────────────
        for batch_size in (50, 10, 1):
            if batch_size == 1 and total > 100:
                log.warning(f"Row-by-row recovery for '{table_name}' ({total} rows) — this may be slow.")
            self._session.rollback()
            self._recover_in_batches(table, pk_cols, records, batch_size, report, total)
            if report.success_count + len(report.failed_rows) == total:
                break

        return report

    def _recover_in_batches(
        self, table, pk_cols: list[str], records: list[dict],
        batch_size: int, report: EntityLoadReport, total: int,
    ) -> None:
        """Process remaining unprocessed records in batches with savepoint isolation."""
        # Determine which records still need processing (not yet succeeded or failed)
        succeeded_ids = set()
        failed_count = len(report.failed_rows)
        processed_count = report.success_count + failed_count

        batch_start = 0
        remaining = records[processed_count:] if batch_size > 1 else records

        if batch_size > 1:
            for i in range(0, len(remaining), batch_size):
                batch = remaining[i : i + batch_size]
                try:
                    with self._session.begin_nested():
                        self._execute_upsert(table, pk_cols, batch)
                    report.success_count += len(batch)
                    log.debug(
                        f"Tier {batch_size}: {report.success_count}/{total} "
                        f"rows loaded for '{report.table_name}'"
                    )
                except Exception:
                    log.debug(
                        f"Batch of {len(batch)} failed in '{report.table_name}'. "
                        f"Will retry at smaller batch size."
                    )
                    self._session.rollback()
        else:
            # Row-by-row (batch_size == 1)
            for record in remaining:
                try:
                    with self._session.begin_nested():
                        self._execute_upsert(table, pk_cols, [record])
                    report.success_count += 1
                except Exception as exc:
                    report.failed_rows.append(record)
                    report.errors.append(str(exc))

        if report.success_count + len(report.failed_rows) < total and batch_size > 1:
            # Some records still unprocessed — will be picked up by next batch_size tier
            pass

    def _execute_upsert(self, table, pk_cols: list[str], records: list[dict]) -> None:
        """Helper to execute a PG upsert statement.

        Tables listed in DEDUP_CONFLICT_COLUMNS use ON CONFLICT DO NOTHING
        against their business-key columns (natural dedup); all other tables
        use the default primary-key upsert behaviour.
        """
        stmt = pg_insert(table).values(records)
        table_name = table.name if hasattr(table, "name") else str(table)
        dedup_cols = DEDUP_CONFLICT_COLUMNS.get(table_name)

        if dedup_cols:
            stmt = stmt.on_conflict_do_nothing(index_elements=dedup_cols)
        else:
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
