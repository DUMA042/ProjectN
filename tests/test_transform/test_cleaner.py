"""
tests/test_transform/test_cleaner.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for owl.transform.cleaner functions.
"""

from __future__ import annotations

import pandas as pd
import pytest

from owl.transform.cleaner import (
    coerce_dates,
    coerce_numerics,
    drop_blank_columns,
    drop_blank_rows,
    drop_duplicates,
    handle_nulls,
    normalise_column_names,
    remove_invisible_chars,
    strip_whitespace,
)


class TestDropBlankRows:
    def test_removes_fully_blank_rows(self, dirty_df):
        result = drop_blank_rows(dirty_df)
        # Row 2 (index 2) is fully blank → should be gone
        assert len(result) < len(dirty_df)

    def test_preserves_partially_populated_rows(self, sample_flat_df):
        result = drop_blank_rows(sample_flat_df)
        assert len(result) == len(sample_flat_df)


class TestNormaliseColumnNames:
    def test_converts_to_snake_case(self):
        df = pd.DataFrame(columns=["Employee ID", "Full Name", "Date Of Birth"])
        result = normalise_column_names(df)
        assert list(result.columns) == ["employee_id", "full_name", "date_of_birth"]

    def test_strips_special_chars(self):
        df = pd.DataFrame(columns=["Name (First)", "Date!"])
        result = normalise_column_names(df)
        assert list(result.columns) == ["name_first", "date"]


class TestCoerceDates:
    def test_valid_dates_parsed(self):
        df = pd.DataFrame({"date": ["2024-01-15", "2024-02-20"]})
        result = coerce_dates(df, ["date"])
        assert result["date"].dtype == "datetime64[ns]"

    def test_invalid_dates_become_nat(self):
        df = pd.DataFrame({"date": ["not-a-date", "2024-01-15"]})
        result = coerce_dates(df, ["date"])
        assert result["date"].isna().sum() == 1


class TestDropDuplicates:
    def test_removes_exact_duplicates(self, dirty_df):
        result = drop_duplicates(dirty_df)
        assert len(result) < len(dirty_df)
