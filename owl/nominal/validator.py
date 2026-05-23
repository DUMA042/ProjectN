"""
owl.nominal.validator
~~~~~~~~~~~~~~~~~~~~~
NominalFileValidator — Stage 4 validation for Nominal Roll files.

Validates:
  1. Column-position signature (9 authoritative positions)
  2. At least one data row below the header
  3. No blank id_no values (col 3)
  4. No duplicate id_no values within the file
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from owl.logger import get_logger

log = get_logger(__name__)

# ── Column Signature ─────────────────────────────────────────────────────────
# 0-indexed column positions and the expected header text (case/whitespace insensitive).
NOMINAL_SIGNATURE: dict[int, str] = {
    1:  "name",
    3:  "id no.",
    11: "geographical zone",
    12: "gl",
    14: "rank",
    15: "department",
    17: "location",
    25: "employment type",
    28: "date of last deployment",
}


def _normalise_header(value: Any) -> str:
    """Lowercase, strip, collapse whitespace for header comparison."""
    if value is None:
        return ""
    return " ".join(str(value).lower().split())


@dataclass
class SignatureCheckResult:
    """Result of column-position signature verification."""
    passed: bool
    mismatches: list[dict] = field(default_factory=list)


def check_signature(df_raw: pd.DataFrame) -> SignatureCheckResult:
    """Verify the 9 authoritative column positions on row 0 (the header row).

    Parameters
    ----------
    df_raw:
        A DataFrame read with ``header=None`` so row 0 is the actual header.

    Returns
    -------
    SignatureCheckResult
    """
    mismatches = []
    header_row = df_raw.iloc[0] if len(df_raw) > 0 else pd.Series(dtype=object)

    for col_idx, expected in NOMINAL_SIGNATURE.items():
        if col_idx >= len(header_row):
            mismatches.append({
                "col_idx": col_idx,
                "expected": expected,
                "actual": "<column missing>",
            })
            continue
        actual = _normalise_header(header_row.iloc[col_idx])
        if actual != expected:
            mismatches.append({
                "col_idx": col_idx,
                "expected": expected,
                "actual": actual,
            })

    return SignatureCheckResult(passed=len(mismatches) == 0, mismatches=mismatches)


@dataclass
class ValidationResult:
    """Outcome of NominalFileValidator.validate()."""
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    duplicate_id_nos: list[str] = field(default_factory=list)


class NominalFileValidator:
    """Validates a Nominal Roll Excel file before processing.

    Usage
    -----
    >>> validator = NominalFileValidator(file_path)
    >>> result = validator.validate()
    >>> if not result.valid:
    ...     for err in result.errors:
    ...         print(err)
    """

    # Column index for id_no in the data rows
    COL_ID_NO = 3

    def __init__(self, file_path: str | Path) -> None:
        self._file_path = Path(file_path)

    def validate(self) -> ValidationResult:
        """Run all validation checks and return a consolidated result."""
        result = ValidationResult(valid=True)

        # ── Step 1: Read the raw file ─────────────────────────────────────────
        try:
            df_raw = pd.read_excel(self._file_path, header=None)
        except Exception as exc:
            result.valid = False
            result.errors.append(f"Cannot read file: {exc}")
            return result

        # ── Step 2: Column signature ──────────────────────────────────────────
        sig = check_signature(df_raw)
        if not sig.passed:
            result.valid = False
            for m in sig.mismatches:
                result.errors.append(
                    f"Signature mismatch at col {m['col_idx']}: "
                    f"expected '{m['expected']}', got '{m['actual']}'"
                )
            # Cannot proceed with further checks if signature fails
            return result

        # ── Step 3: Minimum row count ─────────────────────────────────────────
        data_rows = df_raw.iloc[1:]  # Skip header row
        if len(data_rows) == 0:
            result.valid = False
            result.errors.append("File has no data rows below the header.")
            return result

        # ── Step 4: Blank id_no check ─────────────────────────────────────────
        id_no_series = data_rows.iloc[:, self.COL_ID_NO]
        blank_mask = id_no_series.apply(lambda v: _is_blank_id(v))
        blank_rows = data_rows.index[blank_mask].tolist()
        if blank_rows:
            result.valid = False
            for r in blank_rows:
                result.errors.append(f"Row {r + 1} (1-indexed): id_no is blank.")

        # ── Step 5: Intra-file duplicate id_no check ─────────────────────────
        parsed_ids = id_no_series.apply(_parse_id_no)
        valid_ids = parsed_ids.dropna()
        dupes = valid_ids[valid_ids.duplicated(keep=False)]
        if not dupes.empty:
            result.valid = False
            dupe_values = sorted(dupes.unique().tolist())
            result.duplicate_id_nos = dupe_values
            result.errors.append(
                f"Duplicate id_no values found within the file "
                f"({len(dupe_values)} unique IDs appear more than once): "
                + ", ".join(str(d) for d in dupe_values[:10])
                + (" ..." if len(dupe_values) > 10 else "")
            )

        return result


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_blank_id(value: Any) -> bool:
    """Return True if an id_no cell is empty/null."""
    if value is None:
        return True
    if isinstance(value, float):
        import math
        return math.isnan(value)
    s = str(value).strip()
    return not s or s.lower() in ("nan", "none", "")


def _parse_id_no(value: Any) -> str | None:
    """Convert id_no cell to a canonical string, or None if blank."""
    if _is_blank_id(value):
        return None
    s = str(value).strip()
    try:
        return str(int(float(s)))
    except (ValueError, TypeError):
        return s
