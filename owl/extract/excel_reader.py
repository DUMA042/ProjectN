"""
owl.extract.excel_reader
~~~~~~~~~~~~~~~~~~~~~~~~
Robust Excel ingestion engine.

Responsibilities
----------------
* Open an .xlsx / .xls file via openpyxl (read-only for performance).
* Unmerge merged cells and forward-fill their values so every logical cell
  holds an explicit value — a pre-condition for any DataFrame work.
* Detect and skip purely decorative / blank rows above the real header.
* Return a dict mapping sheet name → pd.DataFrame for every requested sheet
  (defaults to *all* sheets).

This module is intentionally I/O-only. No business logic, no validation.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Generator

import openpyxl
import pandas as pd
from openpyxl.worksheet.worksheet import Worksheet

from owl.exceptions import ExtractionError
from owl.logger import get_logger

log = get_logger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _iter_merged_ranges(ws: Worksheet) -> Generator[tuple[int, int, int, int], None, None]:
    """Yield (min_row, min_col, max_row, max_col) for each merged range."""
    for merge in ws.merged_cells.ranges:
        yield merge.min_row, merge.min_col, merge.max_row, merge.max_col


def _unmerge_and_fill(ws: Worksheet) -> None:
    """Unmerge all merged cells in *ws* and forward-fill the top-left value.

    openpyxl stores the value only in the top-left cell of a merged range.
    After unmerging, the remaining cells are ``None``. This function copies
    the top-left value into every cell of the former range so downstream
    pandas operations see consistent data.
    """
    # Snapshot ranges before iterating (ws.merged_cells changes during iteration)
    ranges = list(_iter_merged_ranges(ws))

    for min_row, min_col, max_row, max_col in ranges:
        # Capture the anchor value before unmerging.
        anchor_value = ws.cell(min_row, min_col).value
        ws.unmerge_cells(
            start_row=min_row,
            start_column=min_col,
            end_row=max_row,
            end_column=max_col,
        )
        # Fill every cell in the former range with the anchor value.
        for row in range(min_row, max_row + 1):
            for col in range(min_col, max_col + 1):
                ws.cell(row, col).value = anchor_value

    if ranges:
        log.debug(f"Unmerged and filled {len(ranges)} merged range(s).")


def _sheet_to_dataframe(ws: Worksheet, header_row: int | None = 1) -> pd.DataFrame:
    """Convert an openpyxl worksheet to a pandas DataFrame."""
    data = list(ws.iter_rows(values_only=True))
    if not data:
        log.warning(f"Sheet '{ws.title}' is empty — returning empty DataFrame.")
        return pd.DataFrame()

    if header_row is None:
        # Raw data read
        df = pd.DataFrame(data)
        df.columns = [f"col_{i}" for i in range(len(df.columns))]
    else:
        headers = [str(h).strip() if h is not None else f"col_{i}" for i, h in enumerate(data[header_row - 1])]
        rows = data[header_row:]  # everything below the header row
        df = pd.DataFrame(rows, columns=headers)

    # Strip leading/trailing whitespace from string cells.
    str_cols = df.select_dtypes(include="object").columns
    df[str_cols] = df[str_cols].apply(lambda s: s.str.strip() if s.dtype == "object" else s)

    return df



# ── Main class ────────────────────────────────────────────────────────────────

class ExcelReader:
    """Primary entry point for ingesting a single Excel file.

    Parameters
    ----------
    file_path:
        Absolute or relative path to the .xlsx / .xls file.
    sheet_names:
        Specific sheet names to read.  ``None`` (default) reads *all* sheets.
    header_row:
        1-indexed row number to treat as the column header.  Override per-sheet
        via ``per_sheet_header_rows``.
    per_sheet_header_rows:
        Dict mapping sheet name → header row int, for sheets with non-standard
        layouts (e.g., title rows above the actual data table).

    Example
    -------
    >>> reader = ExcelReader("nest/attendance.xlsx")
    >>> frames = reader.read()
    >>> df_jan = frames["January"]
    """

    def __init__(
        self,
        file_path: str | Path,
        sheet_names: list[str] | None = None,
        header_row: int = 1,
        per_sheet_header_rows: dict[str, int] | None = None,
    ) -> None:
        self._path = Path(file_path)
        self._sheet_names = sheet_names
        self._default_header_row = header_row
        self._per_sheet_header_rows: dict[str, int] = per_sheet_header_rows or {}

    # ── Public API ────────────────────────────────────────────────────────────

    def read(self) -> dict[str, pd.DataFrame]:
        """Read the Excel file and return a dict of {sheet_name: DataFrame}.

        Returns
        -------
        dict[str, pd.DataFrame]

        Raises
        ------
        ExtractionError
            If the file does not exist, cannot be opened, or a requested sheet
            is not found.
        """
        self._validate_file()

        log.info(f"Opening workbook: {self._path.name}")
        wb = None
        try:
            # Using read_only=True is significantly faster and less prone to file locking on Windows.
            wb = openpyxl.load_workbook(self._path, read_only=True, data_only=True)
            target_sheets = self._resolve_sheet_names(wb)


            results: dict[str, pd.DataFrame] = {}

            for name in target_sheets:
                log.info(f"Processing sheet: '{name}'")
                ws = wb[name]
                if not wb.read_only:
                    _unmerge_and_fill(ws)

                header_row = self._per_sheet_header_rows.get(name, self._default_header_row)
                df = _sheet_to_dataframe(ws, header_row=header_row)
                results[name] = df
                log.debug(f"Sheet '{name}' → {df.shape[0]} rows × {df.shape[1]} columns.")

            log.info(f"Finished reading {len(results)} sheet(s) from '{self._path.name}'.")
            return results
        except Exception as exc:
            msg = f"Failed to extract sheets from '{self._path.name}': {exc}"
            log.error(msg)
            raise ExtractionError(msg) from exc
        finally:
            if wb:
                try:
                    wb.close()
                except Exception:
                    pass
            import gc
            gc.collect()



    # ── Private helpers ───────────────────────────────────────────────────────

    def _validate_file(self) -> None:
        if not self._path.exists():
            raise ExtractionError(
                f"File not found: '{self._path}'.",
                context={"path": str(self._path)},
            )
        if not self._path.is_file():
            raise ExtractionError(
                f"Path is not a file: '{self._path}'.",
                context={"path": str(self._path)},
            )
        if self._path.suffix.lower() not in {".xlsx", ".xls", ".xlsm"}:
            raise ExtractionError(
                f"Unsupported file extension '{self._path.suffix}'.",
                context={"path": str(self._path)},
            )

    def _resolve_sheet_names(self, wb: openpyxl.Workbook) -> list[str]:
        available = wb.sheetnames
        if self._sheet_names is None:
            return available

        missing = [s for s in self._sheet_names if s not in available]
        if missing:
            raise ExtractionError(
                f"Requested sheet(s) not found in workbook: {missing}.",
                context={"requested": self._sheet_names, "available": available},
            )
        return self._sheet_names
