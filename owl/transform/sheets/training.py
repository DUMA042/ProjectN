"""
owl.transform.sheets.training
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Decomposes Training data and handles orphan detection (Option A).

Key design decisions
--------------------
* Uses ``DimensionCache`` (passed via context["dim_cache"]) to resolve
  venue / consultant / location names to their real database PKs.
  This guarantees valid foreign keys in employee_trainings without
  generating incorrect MD5-based surrogate keys.
* Orphaned rows (unknown id_no) are routed to quarantine_trainings with
  the human-readable name columns that table actually expects.
* Date parsing is guarded per-row so one bad date cell does not abort
  the entire file.
"""

from __future__ import annotations

import pandas as pd
from owl.transform.normalizer import BaseNormalizer, NormalizationResult
from owl.logger import get_logger

log = get_logger(__name__)

# Values that should be treated as "empty" in the id_no column
_NULL_ID_VALUES = {"nan", "none", "nat", "", "0"}


class TrainingNormalizer(BaseNormalizer):
    """
    Normalizer for Training Records.
    Implements Option A: Quarantine records for unknown employee IDs.
    """

    def decompose(self) -> NormalizationResult:
        df = self._source.copy()

        # ── 1. Normalise column headers ──────────────────────────────────────
        df.columns = [str(c).lower().strip().replace(" ", "_") for c in df.columns]

        # Map known id-column name variants to the canonical 'id_no'
        for alias in ("id", "staff_id", "staffid", "employee_id"):
            if alias in df.columns and "id_no" not in df.columns:
                df = df.rename(columns={alias: "id_no"})
                break

        if "id_no" not in df.columns:
            raise KeyError(
                f"Required id column not found. Columns present: {df.columns.tolist()}"
            )

        # ── 2. Sanitise id_no column ─────────────────────────────────────────
        df["id_no"] = df["id_no"].astype(str).str.strip()
        # Exclude phantom null values that would look like valid IDs
        df = df[~df["id_no"].str.lower().isin(_NULL_ID_VALUES)]

        # ── 3. Orphan detection ───────────────────────────────────────────────
        valid_ids: set = self._context.get("valid_ids", set())
        dim_cache = self._context.get("dim_cache")

        mask_orphan = ~df["id_no"].isin(valid_ids)
        orphans    = df[mask_orphan].copy()
        valid_recs = df[~mask_orphan].copy()

        entities: dict = {}

        if not orphans.empty:
            self._warn(
                f"Option A: Quarantined {len(orphans)} training record(s) "
                f"with unknown id_no."
            )
            entities["quarantine_trainings"] = self._build_quarantine_df(orphans)

        if valid_recs.empty:
            log.warning("TrainingNormalizer: no valid records remain after orphan check.")
            return NormalizationResult(entities=entities, warnings=self._warnings)

        # ── 4. Resolve dimension IDs via DimensionCache ───────────────────────
        if dim_cache is None:
            # Graceful degradation: leave FK columns as None so the loader
            # can still insert the fact rows (FKs are nullable).
            log.warning(
                "TrainingNormalizer: no DimensionCache in context — "
                "venue_id / consultant_id / location_id will be NULL."
            )
            valid_recs["venue_id"]      = None
            valid_recs["consultant_id"] = None
            valid_recs["location_id"]   = None
        else:
            valid_recs["venue_id"] = valid_recs.get("venue", pd.Series(dtype=str)).apply(
                lambda x: dim_cache.get_or_create_venue(x) if pd.notna(x) else None
            )
            valid_recs["consultant_id"] = valid_recs.get(
                "consultant", pd.Series(dtype=str)
            ).apply(
                lambda x: dim_cache.get_or_create_consultant(x) if pd.notna(x) else None
            )
            valid_recs["location_id"] = valid_recs.get("location", pd.Series(dtype=str)).apply(
                lambda x: dim_cache.get_or_create_location(x) if pd.notna(x) else None
            )

        # ── 5. Parse dates with per-row safety ───────────────────────────────
        valid_recs["start_date"] = self._safe_parse_dates(valid_recs, "start_date")
        valid_recs["end_date"]   = self._safe_parse_dates(valid_recs, "end_date")

        # ── 6. Build fact table ───────────────────────────────────────────────
        # Ensure optional columns exist (newer Excel versions may have extra columns)
        for col in ("title",):
            if col not in valid_recs.columns:
                valid_recs[col] = None

        final_cols = ["id_no", "venue_id", "consultant_id", "location_id",
                      "start_date", "end_date", "title"]
        entities["employee_trainings"] = valid_recs[final_cols].copy()

        log.info(
            f"TrainingNormalizer: {len(valid_recs)} valid record(s) prepared, "
            f"{len(orphans)} quarantined."
        )
        return NormalizationResult(entities=entities, warnings=self._warnings)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _build_quarantine_df(self, orphans: pd.DataFrame) -> pd.DataFrame:
        """Map orphan rows to the quarantine_trainings schema."""
        q = orphans.copy()

        # Rename raw text columns to what the quarantine table expects
        col_map = {
            "venue":      "venue_name",
            "consultant": "consultant_name",
        }
        q = q.rename(columns={k: v for k, v in col_map.items() if k in q.columns})

        # Parse dates safely for the quarantine table too
        q["start_date"] = self._safe_parse_dates(q, "start_date")
        q["end_date"]   = self._safe_parse_dates(q, "end_date")

        # Ensure optional columns exist
        for col in ("title",):
            if col not in q.columns:
                q[col] = None

        # Keep only the columns the quarantine model accepts
        keep = ["id_no", "venue_name", "consultant_name", "start_date", "end_date", "title"]
        keep = [c for c in keep if c in q.columns]
        return q[keep]

    @staticmethod
    def _safe_parse_dates(df: pd.DataFrame, col: str) -> pd.Series:
        """Parse a date column row-by-row, returning None for unparseable cells."""
        if col not in df.columns:
            return pd.Series([None] * len(df), index=df.index)

        result = []
        for val in df[col]:
            try:
                parsed = pd.to_datetime(val, errors="raise")
                result.append(parsed.date() if pd.notna(parsed) else None)
            except Exception:
                log.warning(f"TrainingNormalizer: unparseable date value '{val}' → stored as None.")
                result.append(None)
        return pd.Series(result, index=df.index)
