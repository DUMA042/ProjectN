"""
owl.transform.dimension_cache
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In-memory cache for dimension tables (venues, consultants, locations).

Purpose
-------
When processing Training files, the fact table (employee_trainings) needs
real database-assigned integer IDs as foreign keys — not hashed surrogates.

This cache solves the problem in three steps:
  1. Loads all existing dimension rows from the database once at startup
     (one bulk SELECT per table, never repeated).
  2. Provides O(1) dictionary lookups for every row in the source file.
  3. Auto-inserts any genuinely new name it has not seen before, using
     PostgreSQL RETURNING to capture the real auto-increment ID, and
     immediately stores it back in the cache so subsequent rows with the
     same name do not hit the database again.

Usage
-----
    cache = DimensionCache(session)
    venue_id = cache.get_or_create_venue("Doha, Qatar")
    consultant_id = cache.get_or_create_consultant("Blue Hero limited")
    location_id = cache.get_or_create_location("HQ")
"""

from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from owl.load.models import Venue, Consultant, Location
from owl.logger import get_logger

log = get_logger(__name__)


class DimensionCache:
    """Thread-local in-memory cache for dimension tables used in Training ingestion.

    Parameters
    ----------
    session:
        An active SQLAlchemy Session that will be used for any INSERT operations.
        The caller is responsible for committing or rolling back this session.
    """

    def __init__(self, session: Session) -> None:
        self._session = session
        self._venues:      dict[str, int] = {}
        self._consultants: dict[str, int] = {}
        self._locations:   dict[str, int] = {}
        self._load_all()

    # ── Public API ─────────────────────────────────────────────────────────────

    def get_or_create_venue(self, name: str) -> int | None:
        """Return the venue_id for *name*, inserting a new row if necessary."""
        return self._get_or_create(
            cache=self._venues,
            raw_name=name,
            model=Venue,
            id_col="venue_id",
            name_col="venue_name",
        )

    def get_or_create_consultant(self, name: str) -> int | None:
        """Return the consultant_id for *name*, inserting a new row if necessary."""
        return self._get_or_create(
            cache=self._consultants,
            raw_name=name,
            model=Consultant,
            id_col="consultant_id",
            name_col="consultant_name",
        )

    def get_or_create_location(self, name: str) -> int | None:
        """Return the location_id for *name*, inserting a new row if necessary."""
        return self._get_or_create(
            cache=self._locations,
            raw_name=name,
            model=Location,
            id_col="location_id",
            name_col="location_name",
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    def _load_all(self) -> None:
        """Bulk-load all three dimension tables into memory in one pass each."""
        log.debug("DimensionCache: loading venues, consultants, locations from DB...")

        for row in self._session.query(Venue).all():
            self._venues[self._normalise(row.venue_name)] = row.venue_id

        for row in self._session.query(Consultant).all():
            self._consultants[self._normalise(row.consultant_name)] = row.consultant_id

        for row in self._session.query(Location).all():
            self._locations[self._normalise(row.location_name)] = row.location_id

        log.debug(
            f"DimensionCache: loaded {len(self._venues)} venues, "
            f"{len(self._consultants)} consultants, "
            f"{len(self._locations)} locations."
        )

    def _get_or_create(
        self,
        cache: dict[str, int],
        raw_name: str,
        model,
        id_col: str,
        name_col: str,
    ) -> int | None:
        """Return the ID for *raw_name* from cache, inserting if not found."""
        if not raw_name or str(raw_name).strip().lower() in ("nan", "none", ""):
            return None

        key = self._normalise(raw_name)
        if key in cache:
            return cache[key]

        # ── Cache miss: insert new row and capture the real PK ─────────────
        clean_name = str(raw_name).strip()
        log.info(f"DimensionCache: new entry in '{model.__tablename__}' -> '{clean_name}'")

        try:
            table = model.__table__
            stmt = (
                pg_insert(table)
                .values({name_col: clean_name})
                .on_conflict_do_nothing()   # race-safe: if another process inserted it
                .returning(table.c[id_col])
            )
            result = self._session.execute(stmt)
            row = result.fetchone()

            if row is None:
                # Row already existed (inserted by a concurrent process between
                # our SELECT and INSERT). Re-query to get the real ID.
                existing = (
                    self._session.query(getattr(model, id_col))
                    .filter(getattr(model, name_col) == clean_name)
                    .scalar()
                )
                new_id = existing
            else:
                new_id = row[0]

            self._session.flush()   # Make ID visible within the same transaction
            cache[key] = new_id
            log.debug(f"DimensionCache: '{clean_name}' saved as {id_col}={new_id}")
            return new_id

        except Exception as exc:
            log.error(f"DimensionCache: failed to upsert '{clean_name}' into {model.__tablename__}: {exc}")
            return None

    @staticmethod
    def _normalise(name: str) -> str:
        """Return a case-folded, stripped key for consistent dictionary lookups."""
        return str(name).strip().lower()
