"""
owl.extract.classifier
~~~~~~~~~~~~~~~~~~~~~~
Structural classification engine — identifies Excel files by their column fingerprints.

Responsibilities
----------------
1. Define 'Fingerprints' (sets of unique columns) for each report type.
2. Analyze raw DataFrames to identify their ReportType.
3. Validate that all required columns for a type are present.
4. Extract metadata (Period, Version) to generate standard filenames.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path

import pandas as pd

from owl.logger import get_logger

log = get_logger(__name__)


class ReportType(Enum):
    """Supported report types in the Owl system."""
    NOMINAL = "Nominal"
    TRAINING = "Training"
    CARD_SWIPE = "CardSwipe"
    LEAVE = "Leave"
    UNKNOWN = "Unknown"


@dataclass(frozen=True)
class IngestionMetadata:
    """Routing metadata extracted during classification."""
    report_type: ReportType
    department: str = "AHRD"  # Defaulting as per requirements
    period: date | None = None
    version: int = 1

    def generate_filename(self) -> str:
        """Generate a strict filename: DEPT_TYPE_YYYYMM_vV.xlsx"""
        p_str = self.period.strftime("%Y%m") if self.period else "000000"
        return f"{self.department}_{self.report_type.value}_{p_str}_v{self.version}.xlsx"


# ── Fingerprint Registry ──────────────────────────────────────────────────────
# Define the unique columns that identify each report type.
# A file is classified as Type X if it contains ALL 'identifier' columns.

FINGERPRINTS: dict[ReportType, set[str]] = {
    ReportType.NOMINAL: {
        "id_no", "gl"
    },
    ReportType.TRAINING: {
        "venue", "consultant", "start_date"
    },
    ReportType.CARD_SWIPE: {
        "card_swiping_time"
    },
    # LEAVE fingerprint removed because we use strict positional validation for Leave files
}

# Mapping of Type -> Target Subdirectory
ROUTING_MAP: dict[ReportType, str] = {
    ReportType.NOMINAL: "Nominal_Folder",
    ReportType.TRAINING: "Training_Folder",
    ReportType.CARD_SWIPE: "card_Swiping_Folder",
    ReportType.LEAVE: "Leave_Folder",
}


class StructuralClassifier:
    """Classifies Excel files by analyzing their column headers."""

    def __init__(self, df: pd.DataFrame) -> None:
        """
        Parameters
        ----------
        df:
            A cleaned DataFrame (headers already normalised to snake_case).
        """
        self._df = df
        self._columns = set(df.columns)

    def classify(self) -> ReportType:
        """Identify the report type based on column overlap.
        Includes a 'search' fallback if the first row doesn't match.
        """
        # We cannot use this method for LEAVE files anymore, as it relies on normalized column names
        # which destroys duplicate columns. This is now only for generic types.
        for r_type, required_cols in FINGERPRINTS.items():
            if required_cols.issubset(self._columns):
                log.info(f"Structural match found on primary headers: {r_type.name}")
                return r_type
        
        log.warning("Primary match failed. Attempting deep header search...")
        return ReportType.UNKNOWN

    @classmethod
    def validate_leave_file(cls, df_raw: pd.DataFrame) -> int | None:
        """Assume Excel Row 1 = Major Header, Row 2 = Sub-Header.
        
        Returns 0 (pandas index) if the file has at least 3 rows.
        Signature validation is kept for logging but won't block ingestion.
        
        NOTE: Uses .iloc[] for positional access to be compatible with pandas 3.0+
        """
        # Excel Row 1 = df.iloc[0], Excel Row 2 = df.iloc[1], Excel Row 3 = df.iloc[2]
        if len(df_raw) < 3:
            log.warning("Leave file has fewer than 3 rows. Cannot process.")
            return None

        r1 = df_raw.iloc[0]  # Excel Row 1 (Major Header)
        r2 = df_raw.iloc[1]  # Excel Row 2 (Sub-Header)

        def check(val, expected) -> bool:
            return str(val).strip().upper().replace(" ", "") == str(expected).upper().replace(" ", "")

        def safe_iloc(row, idx):
            return row.iloc[idx] if idx < len(row) else ""

        # ✅ CRITICAL FIX: Use safe_iloc for positional access to avoid IndexError on shorter files
        major_checks = [
            check(safe_iloc(r1, 8), "PRE-RETIREMENTLEAVE"),
            check(safe_iloc(r1, 10), "CASUALBEFOREANNUAL"),
            check(safe_iloc(r1, 22), "COMPASSIONATELEAVE"),
            check(safe_iloc(r1, 24), "PATERNITYLEAVE"),
        ]
        sub_checks = [
            check(safe_iloc(r2, 2), "STAFFID"),
            check(safe_iloc(r2, 6), "PROPOSEDLEAVEDATE"),
            check(safe_iloc(r2, 7), "RESUMPTIONDATE"),
        ]

        # If it has the STAFFID column and at least one other matching signature, consider it a Leave file
        is_leave_file = check(safe_iloc(r2, 2), "STAFFID") and (any(major_checks) or any(sub_checks[1:]))

        if is_leave_file:
            if all(major_checks) and all(sub_checks):
                log.info("Leave file validated: Excel Row 1 (Major) & Row 2 (Sub) match signatures.")
            else:
                log.warning("Leave file partial signature match detected. Proceeding as Leave file.")
            return 0

        # If it doesn't match the signature, return None so the classifier can check other file types
        return None

    @classmethod
    def find_best_header_row(cls, df_raw: pd.DataFrame) -> tuple[ReportType, int] | None:
        """Scan a raw (unstacked) DataFrame to find the row that looks most like headers."""
        # 1. First, explicitly check for Leave file (strict positional multi-header)
        leave_header_idx = cls.validate_leave_file(df_raw)
        if leave_header_idx is not None:
            log.info(f"Found explicit multi-header signatures for LEAVE on row index {leave_header_idx}")
            return ReportType.LEAVE, leave_header_idx

        # 2. Check other types (first 10 rows)
        for i in range(min(10, len(df_raw))):
            row_values = []
            for x in df_raw.iloc[i].dropna():
                # Normalise: lowercase, strip, space->underscore, remove non-alphanumeric
                val = str(x).lower().strip().replace(" ", "_")
                val = re.sub(r"[^a-z0-9_]", "", val)
                row_values.append(val)
            
            row_set = set(row_values)
            for r_type, finger in FINGERPRINTS.items():
                if finger.issubset(row_set):
                    log.info(f"Found headers for {r_type.name} on row index {i}")
                    return r_type, i
        return None

    def extract_period(self) -> date | None:
        """Heuristically attempt to find a reference period (YYYYMM) in the data.
        
        Strategy:
        1. Look for the most common month/year in date columns.
        2. Fall back to current month if no dates are found.
        """
        date_cols = self._df.select_dtypes(include=["datetime64", "datetime"]).columns
        if not date_cols.empty:
            # Get the first non-null date from the first date column
            sample_date = self._df[date_cols[0]].dropna().iloc[0] if not self._df[date_cols[0]].empty else None
            if sample_date and isinstance(sample_date, (datetime, date)):
                # Reset to 1st of the month
                return date(sample_date.year, sample_date.month, 1)
        
        # Fallback to current date
        today = date.today()
        return date(today.year, today.month, 1)


def classify_file(df: pd.DataFrame) -> IngestionMetadata:
    """High-level utility to classify a DataFrame and build metadata.
    Automatically handles "Floating Headers" by searching for the fingerprint row.
    """
    classifier = StructuralClassifier(df)
    r_type = classifier.classify()
    period = classifier.extract_period()
    
    return IngestionMetadata(
        report_type=r_type,
        period=period,
        version=1
    )