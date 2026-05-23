"""
tests/test_nominal_signature.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for the NominalSignatureChecker column-position validation.
Covers Test Categories N-T1-04 and N-T2-01 from the test plan.
"""

import pytest
import pandas as pd
from owl.nominal.validator import (
    check_signature,
    NOMINAL_SIGNATURE,
    SignatureCheckResult,
)


def _make_header_row(overrides: dict | None = None) -> list:
    """Build a valid header row as a list, optionally overriding specific positions."""
    # Fill 31 columns with empty strings
    row = [""] * 31
    # Apply the valid signature values
    valid_values = {
        1: "Name",
        3: "ID No.",
        11: "Geographical Zone",
        12: "GL",
        14: "Rank",
        15: "Department",
        17: "Location",
        25: "Employment Type",
        28: "Date of Last Deployment",
    }
    for idx, val in valid_values.items():
        row[idx] = val
    if overrides:
        for idx, val in overrides.items():
            row[idx] = val
    return row


def _df_with_header(header: list) -> pd.DataFrame:
    """Wrap a header row in a DataFrame (header_row=None style)."""
    return pd.DataFrame([header])


class TestValidSignature:
    def test_valid_signature_passes(self):
        header = _make_header_row()
        df = _df_with_header(header)
        result = check_signature(df)
        assert result.passed is True
        assert result.mismatches == []

    def test_case_insensitive_match(self):
        """Headers with different casing should still pass."""
        header = _make_header_row({
            1: "NAME",
            3: "ID NO.",
            11: "GEOGRAPHICAL ZONE",
        })
        df = _df_with_header(header)
        result = check_signature(df)
        assert result.passed is True

    def test_whitespace_variations_pass(self):
        """Extra surrounding whitespace in header values should be stripped."""
        header = _make_header_row({
            1: "  Name  ",
            3: "  ID No.  ",
        })
        df = _df_with_header(header)
        result = check_signature(df)
        assert result.passed is True


class TestInvalidSignature:
    def test_missing_geographical_zone_fails(self):
        header = _make_header_row({11: "Zone"})
        df = _df_with_header(header)
        result = check_signature(df)
        assert result.passed is False
        col_indices = [m["col_idx"] for m in result.mismatches]
        assert 11 in col_indices

    def test_missing_employment_type_fails(self):
        header = _make_header_row({25: "Contract Type"})
        df = _df_with_header(header)
        result = check_signature(df)
        assert result.passed is False
        col_indices = [m["col_idx"] for m in result.mismatches]
        assert 25 in col_indices

    def test_too_few_columns_fails(self):
        """DataFrame with fewer than 29 columns should fail on missing indices."""
        df = pd.DataFrame([["Name", "ID No.", "GL"]])  # only 3 columns
        result = check_signature(df)
        assert result.passed is False
        # Should flag most of the 9 required positions as missing
        assert len(result.mismatches) > 5

    def test_all_9_mismatches_reported(self):
        """An empty row should fail all 9 checks."""
        df = pd.DataFrame([[""] * 31])
        result = check_signature(df)
        assert result.passed is False
        assert len(result.mismatches) == len(NOMINAL_SIGNATURE)

    def test_mismatch_detail_includes_expected_and_actual(self):
        header = _make_header_row({14: "Grade"})  # wrong value at Rank position
        df = _df_with_header(header)
        result = check_signature(df)
        assert result.passed is False
        rank_mismatch = next((m for m in result.mismatches if m["col_idx"] == 14), None)
        assert rank_mismatch is not None
        assert rank_mismatch["expected"] == "rank"
        assert rank_mismatch["actual"] == "grade"
