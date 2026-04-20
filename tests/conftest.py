"""
tests/conftest.py
~~~~~~~~~~~~~~~~~
Shared pytest fixtures for the owl test suite.
"""

from __future__ import annotations

import io
from pathlib import Path

import openpyxl
import pandas as pd
import pytest


# ── Sample DataFrames ──────────────────────────────────────────────────────────

@pytest.fixture()
def sample_flat_df() -> pd.DataFrame:
    """A minimal, clean 'already-extracted' DataFrame for transform tests."""
    return pd.DataFrame(
        {
            "employee_id": ["E001", "E002", "E003"],
            "full_name": ["Alice Ama", "Bob Boateng", "Charlie Ofori"],
            "department": ["HR", "IT", "IT"],
            "date": ["2024-01-15", "2024-01-15", "2024-01-16"],
            "status": ["Present", "Absent", "Present"],
        }
    )


@pytest.fixture()
def dirty_df() -> pd.DataFrame:
    """DataFrame with common real-world dirt — blanks, bad types, whitespace."""
    return pd.DataFrame(
        {
            "employee_id": ["E001", "E002", None, "E002"],
            "full_name": ["  Alice  ", "Bob", None, "Bob"],
            "department": ["HR", "IT", None, "IT"],
            "date": ["2024-01-15", "not-a-date", None, "2024-01-15"],
            "status": ["Present", "Absent", None, "Absent"],
        }
    )


@pytest.fixture()
def tmp_excel_file(tmp_path: Path) -> Path:
    """Create a minimal .xlsx file in a temp directory for extraction tests."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["employee_id", "full_name", "date", "status"])
    ws.append(["E001", "Alice Ama", "2024-01-15", "Present"])
    ws.append(["E002", "Bob Boateng", "2024-01-15", "Absent"])

    path = tmp_path / "test_attendance.xlsx"
    wb.save(str(path))
    return path
