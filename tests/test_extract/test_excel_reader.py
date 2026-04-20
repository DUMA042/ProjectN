"""
tests/test_extract/test_excel_reader.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for owl.extract.excel_reader.ExcelReader.
"""

from __future__ import annotations

import pytest

from owl.exceptions import ExtractionError
from owl.extract.excel_reader import ExcelReader


class TestExcelReaderRead:
    def test_reads_all_sheets(self, tmp_excel_file):
        reader = ExcelReader(tmp_excel_file)
        frames = reader.read()
        assert "Sheet1" in frames
        assert len(frames["Sheet1"]) == 2

    def test_raises_on_missing_file(self, tmp_path):
        reader = ExcelReader(tmp_path / "nonexistent.xlsx")
        with pytest.raises(ExtractionError, match="File not found"):
            reader.read()

    def test_raises_on_unsupported_extension(self, tmp_path):
        txt = tmp_path / "data.txt"
        txt.write_text("hello")
        with pytest.raises(ExtractionError, match="Unsupported file extension"):
            ExcelReader(txt).read()

    def test_raises_on_missing_sheet(self, tmp_excel_file):
        reader = ExcelReader(tmp_excel_file, sheet_names=["NonExistent"])
        with pytest.raises(ExtractionError, match="not found in workbook"):
            reader.read()

    def test_returns_dataframe_with_correct_columns(self, tmp_excel_file):
        frames = ExcelReader(tmp_excel_file).read()
        df = frames["Sheet1"]
        assert list(df.columns) == ["employee_id", "full_name", "date", "status"]
