"""
owl.transform.sheets.nominal
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Simplified NominalNormalizer — serial_no and unit_id removed.

NOTE: The full upsert logic (history tracking, per-row transactions,
lookup pre-loading) is handled by owl.nominal.processor.NominalProcessor.
This normalizer is retained for backward compatibility with the generic
Pipeline flow but produces a minimal employees DataFrame only.
"""

from __future__ import annotations

import pandas as pd
from datetime import date, datetime
from typing import Any

from owl.transform.normalizer import BaseNormalizer, NormalizationResult
from owl.logger import get_logger

log = get_logger(__name__)


def _safe_id_no(value: Any) -> str | None:
    """Convert an id_no cell (may be int/float/str) to a clean string.
    
    Returns None if the value is blank or unparseable.
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.lower() in ("nan", "none", ""):
        return None
    # Strip trailing .0 from floats stored as integers in Excel
    try:
        return str(int(float(s)))
    except (ValueError, TypeError):
        return s


def _safe_date(value: Any) -> date | None:
    """Convert an Excel date cell (serial number, datetime, or string) to a date.
    
    Returns None if unparseable.
    """
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    # Excel serial number (integer)
    if isinstance(value, (int, float)):
        try:
            import xlrd  # type: ignore
            return xlrd.xldate_as_datetime(int(value), 0).date()
        except Exception:
            pass
    # ISO string fallback
    try:
        return date.fromisoformat(str(value).strip())
    except (ValueError, TypeError):
        return None


def _safe_str(value: Any) -> str | None:
    """Convert a cell to a stripped string, returning None for blanks."""
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    s = str(value).strip()
    return s if s else None


class NominalNormalizer(BaseNormalizer):
    """
    Normalizer for the Master Nominal Roll.

    Reads columns by 0-based index (authoritative) as defined in the
    Nominal Roll Agent Prompt. Unit column (col 16) is explicitly ignored.
    serial_no is not produced — the column no longer exists on the employees table.

    Column mapping (0-indexed):
      1  → full_name
      2  → sex
      3  → id_no
      11 → geographical_zone
      12 → gl (→ gl_id via lookup)
      14 → rank (→ rank_id via lookup)
      15 → department (→ department_id via lookup)
      17 → location (→ location_id via lookup)
      25 → employment_type (→ emp_type_id via lookup)
      26 → status (→ status_id via lookup)
      27 → remark
      28 → date_of_last_deployment
    """

    # Column index constants
    COL_NAME = 1
    COL_SEX = 2
    COL_ID_NO = 3
    COL_GEO_ZONE = 11
    COL_GL = 12
    COL_RANK = 14
    COL_DEPT = 15
    COL_LOCATION = 17
    COL_EMP_TYPE = 25
    COL_STATUS = 26
    COL_REMARK = 27
    COL_DEPLOYMENT_DATE = 28

    def decompose(self) -> NormalizationResult:
        df = self._source

        entities: dict[str, pd.DataFrame] = {}

        # Check if we have enough columns
        if len(df.columns) < 29:
            self._warn(
                f"NominalNormalizer: DataFrame has only {len(df.columns)} columns; "
                "expected at least 29. Check header detection."
            )
            return NormalizationResult(entities=entities, warnings=self._warnings)

        # ── Extract dimension tables from named columns (post-classification path) ──
        # When called via the generic Pipeline, headers are already normalised.
        # When called via NominalProcessor, processing is by index — this normalizer
        # is only used in the generic Pipeline path for dimension table seeding.

        # Try named-column access first, then fall back to positional
        cols = list(df.columns)

        def _get_col(idx: int, *names: str) -> pd.Series:
            """Get column by named match first, then by index."""
            for name in names:
                if name in df.columns:
                    return df[name]
            try:
                return df.iloc[:, idx]
            except IndexError:
                return pd.Series([None] * len(df))

        rank_series = _get_col(self.COL_RANK, "rank")
        dept_series = _get_col(self.COL_DEPT, "department")
        gl_series = _get_col(self.COL_GL, "gl")
        location_series = _get_col(self.COL_LOCATION, "location")
        status_series = _get_col(self.COL_STATUS, "status")
        emp_type_series = _get_col(self.COL_EMP_TYPE, "employment_type")

        # Build dimension tables (for seeding via generic Pipeline path)
        def _build_lookup_df(series: pd.Series, id_col: str, name_col: str) -> pd.DataFrame:
            vals = series.dropna().astype(str).str.strip().unique()
            vals = [v for v in vals if v and v.lower() not in ("nan", "none")]
            return pd.DataFrame({name_col: vals})

        entities["ranks"] = _build_lookup_df(rank_series, "rank_id", "rank_name")
        entities["departments"] = _build_lookup_df(dept_series, "department_id", "department_name")
        entities["grade_levels"] = _build_lookup_df(gl_series, "gl_id", "gl_name")
        entities["locations"] = _build_lookup_df(location_series, "location_id", "location_name")
        entities["employee_statuses"] = _build_lookup_df(status_series, "status_id", "status_name")
        # NOTE: employment_types are NOT auto-inserted here — handled by NominalProcessor

        # ── Build employees DataFrame ──
        rows = []
        for i, row in df.iterrows():
            id_no = _safe_id_no(row.iloc[self.COL_ID_NO] if len(row) > self.COL_ID_NO else None)
            if not id_no:
                continue  # Skip rows without id_no

            rows.append({
                "id_no": id_no,
                "full_name": _safe_str(row.iloc[self.COL_NAME] if len(row) > self.COL_NAME else None) or "",
                "sex": _safe_str(row.iloc[self.COL_SEX] if len(row) > self.COL_SEX else None),
                "geographical_zone": _safe_str(row.iloc[self.COL_GEO_ZONE] if len(row) > self.COL_GEO_ZONE else None),
                "date_of_last_deployment": _safe_date(row.iloc[self.COL_DEPLOYMENT_DATE] if len(row) > self.COL_DEPLOYMENT_DATE else None),
                "remark": _safe_str(row.iloc[self.COL_REMARK] if len(row) > self.COL_REMARK else None),
                "phone_number": None,  # Not in Nominal Roll file
            })

        if rows:
            emp_df = pd.DataFrame(rows).drop_duplicates(subset=["id_no"])
            entities["employees"] = emp_df
        else:
            entities["employees"] = pd.DataFrame()

        return NormalizationResult(entities=entities, warnings=self._warnings)
