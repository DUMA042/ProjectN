"""
owl.extract.schema_detector
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Heuristic header / layout detector.

Problem
-------
Real-world Excel files often have:
  • Title rows above the actual data table.
  • Sub-header rows (merged across columns) that are not column names.
  • Completely blank rows used as visual separators.

Purpose
-------
Given a raw DataFrame (loaded with no assumed header row), ``SchemaDetector``
scans the rows to find the most probable header row by looking for the row that:
  1. Has the highest density of non-null, string-type cells.
  2. Does not look like a data row (mostly numbers or dates).

This allows ``ExcelReader`` callers to auto-detect ``header_row`` instead of
hardcoding it per sheet.

Usage
-----
    from owl.extract.schema_detector import SchemaDetector

    raw_df = pd.read_excel("nest/attendance.xlsx", header=None)
    detector = SchemaDetector(raw_df)
    header_row = detector.detect_header_row()   # returns 1-indexed int
"""

from __future__ import annotations

import pandas as pd

from owl.logger import get_logger

log = get_logger(__name__)

# The minimum fraction of cells that must be non-null for a row to be a candidate.
_MIN_NON_NULL_FRACTION = 0.5
# The minimum fraction of string-type cells for a candidate to be promoted to header.
_MIN_STRING_FRACTION = 0.6


class SchemaDetector:
    """Heuristic header-row detector for ambiguously formatted Excel sheets.

    Parameters
    ----------
    raw_df:
        A DataFrame loaded with ``header=None`` (openpyxl row tuples as rows).
    max_scan_rows:
        How many rows from the top to scan before giving up (default: 20).
    """

    def __init__(self, raw_df: pd.DataFrame, max_scan_rows: int = 20) -> None:
        self._df = raw_df
        self._max_scan_rows = max_scan_rows

    def detect_header_row(self) -> int:
        """Return the 1-indexed row number most likely to be the header.

        Falls back to ``1`` if no confident candidate is found.

        Returns
        -------
        int
            1-indexed row number.
        """
        scan_limit = min(self._max_scan_rows, len(self._df))

        best_row = 1
        best_score = -1.0

        for idx in range(scan_limit):
            row = self._df.iloc[idx]
            score = self._score_row(row)
            log.debug(f"Row {idx + 1} header score: {score:.3f}")

            if score > best_score:
                best_score = score
                best_row = idx + 1  # convert to 1-indexed

        log.info(f"Detected header row: {best_row} (score={best_score:.3f})")
        return best_row

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _score_row(row: pd.Series) -> float:
        """Score a row on how 'header-like' it looks.

        Scoring criteria
        ----------------
        * High fraction of non-null cells → base score bump.
        * High fraction of string-type cells → positive score.
        * Fraction of numeric-type cells → negative score (data rows have many).
        * Very short or very long string values → slight penalty.

        Returns
        -------
        float
            Score in range [-1.0, 1.0]. Higher means more header-like.
        """
        total = len(row)
        if total == 0:
            return -1.0

        non_null = row.dropna()
        non_null_frac = len(non_null) / total

        if non_null_frac < _MIN_NON_NULL_FRACTION:
            return -1.0  # Row is mostly empty — skip it.

        str_vals = [v for v in non_null if isinstance(v, str)]
        num_vals = [v for v in non_null if isinstance(v, (int, float)) and not isinstance(v, bool)]

        str_frac = len(str_vals) / len(non_null)
        num_frac = len(num_vals) / len(non_null)

        score = str_frac - num_frac

        # Penalise rows where string values are unusually long (likely data cells).
        if str_vals:
            avg_len = sum(len(str(v)) for v in str_vals) / len(str_vals)
            if avg_len > 50:
                score -= 0.3

        return round(score, 4)
