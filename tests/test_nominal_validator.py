"""
tests/test_nominal_validator.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for NominalFileValidator.
Covers Test Categories N-T1-06, N-T6-01, N-T6-02 from the test plan.
"""

import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import patch, MagicMock
from owl.nominal.validator import NominalFileValidator, _parse_id_no, _is_blank_id


# ── Helpers ───────────────────────────────────────────────────────────────────

VALID_HEADER = [""] * 31
VALID_HEADER[1] = "Name"
VALID_HEADER[3] = "ID No."
VALID_HEADER[11] = "Geographical Zone"
VALID_HEADER[12] = "GL"
VALID_HEADER[14] = "Rank"
VALID_HEADER[15] = "Department"
VALID_HEADER[17] = "Location"
VALID_HEADER[25] = "Employment Type"
VALID_HEADER[28] = "Date of Last Deployment"


def _make_data_row(id_no="417") -> list:
    row = [""] * 31
    row[1] = "John Doe"
    row[2] = "M"
    row[3] = id_no
    row[11] = "North-East"
    row[12] = "12"
    row[14] = "Senior Officer"
    row[15] = "Finance"
    row[17] = "Abuja"
    row[25] = "Permanent"
    row[26] = "Active"
    row[27] = ""
    row[28] = None
    return row


def _make_df(rows: list[list]) -> pd.DataFrame:
    return pd.DataFrame([VALID_HEADER] + rows)


# ── _parse_id_no / _is_blank_id unit tests ────────────────────────────────────

class TestIdNoHelpers:
    def test_integer_cell_converted_to_string(self):
        assert _parse_id_no(417) == "417"

    def test_float_cell_strips_decimal(self):
        assert _parse_id_no(417.0) == "417"

    def test_string_integer_cell(self):
        assert _parse_id_no("417") == "417"

    def test_blank_string_is_none(self):
        assert _parse_id_no("") is None

    def test_nan_is_none(self):
        import math
        assert _parse_id_no(float("nan")) is None

    def test_none_is_none(self):
        assert _parse_id_no(None) is None

    def test_is_blank_nan(self):
        import math
        assert _is_blank_id(float("nan")) is True

    def test_is_blank_empty_string(self):
        assert _is_blank_id("") is True

    def test_is_blank_none(self):
        assert _is_blank_id(None) is True

    def test_is_not_blank_valid_int(self):
        assert _is_blank_id(417) is False


# ── NominalFileValidator ──────────────────────────────────────────────────────

class TestNominalFileValidatorWithMockedExcel:
    """Tests that mock pd.read_excel to avoid needing a real file."""

    def _run_validator(self, df: pd.DataFrame):
        with patch("owl.nominal.validator.pd.read_excel", return_value=df):
            validator = NominalFileValidator("fake_file.xlsx")
            return validator.validate()

    def test_valid_file_passes(self):
        df = _make_df([_make_data_row("417"), _make_data_row("538")])
        result = self._run_validator(df)
        assert result.valid is True
        assert result.errors == []

    def test_file_with_no_data_rows_fails(self):
        df = _make_df([])  # header only, no data rows
        result = self._run_validator(df)
        assert result.valid is False
        # Signature passes, then min-row check fires
        assert any("no data rows" in e.lower() for e in result.errors)

    def test_blank_id_no_fails(self):
        rows = [_make_data_row("417"), _make_data_row("")]  # second row blank
        df = _make_df(rows)
        result = self._run_validator(df)
        assert result.valid is False
        assert any("id_no is blank" in e.lower() for e in result.errors)

    def test_duplicate_id_no_fails(self):
        rows = [_make_data_row("417"), _make_data_row("417")]  # duplicate
        df = _make_df(rows)
        result = self._run_validator(df)
        assert result.valid is False
        assert result.duplicate_id_nos == ["417"]

    def test_multiple_duplicates_all_reported(self):
        rows = [
            _make_data_row("100"),
            _make_data_row("100"),
            _make_data_row("200"),
            _make_data_row("200"),
            _make_data_row("300"),  # not a duplicate
        ]
        df = _make_df(rows)
        result = self._run_validator(df)
        assert result.valid is False
        assert "100" in result.duplicate_id_nos
        assert "200" in result.duplicate_id_nos
        assert "300" not in result.duplicate_id_nos

    def test_wrong_signature_fails(self):
        bad_header = VALID_HEADER.copy()
        bad_header[11] = "Some Other Column"
        df = pd.DataFrame([bad_header, _make_data_row("417")])
        result = self._run_validator(df)
        assert result.valid is False
        assert any("signature mismatch" in e.lower() for e in result.errors)

    def test_read_error_fails_gracefully(self):
        with patch("owl.nominal.validator.pd.read_excel", side_effect=Exception("corrupt file")):
            validator = NominalFileValidator("corrupt.xlsx")
            result = validator.validate()
        assert result.valid is False
        assert any("cannot read file" in e.lower() for e in result.errors)
