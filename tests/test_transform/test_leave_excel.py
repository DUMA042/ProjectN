"""Leave sheet end-to-end: synthetic Excel workbook -> entity DataFrames.

Covers the DD/MM/YYYY business rule at the sheet level (ambiguous dates),
ISO stability, garbage handling, and orphan quarantine — the full
sheet-to-entity path, not just the date parser.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import openpyxl
import pandas as pd

from owl.transform.sheets.leave import LeaveNormalizer

HEADERS = ["Staff ID", "Leave Type", "Proposed Leave Date", "Resumption Date", "Issuance Date"]


def _workbook(path: Path) -> Path:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Leave"
    ws.append(HEADERS)
    # Ambiguous DD/MM/YYYY strings: must read day-first.
    ws.append(["E001", "Annual", "01/05/2026", "05/05/2026", "28/04/2026"])
    # ISO control: unaffected by day-first.
    ws.append(["E002", "Sick", "2026-06-01", "2026-06-03", "2026-05-30"])
    # Garbage dates: row must not produce a leave record.
    ws.append(["E003", "Casual", "PENDING", "PENDING", "PENDING"])
    # Unknown staff: quarantined, never loaded.
    ws.append(["E999", "Annual", "01/07/2026", "03/07/2026", "30/06/2026"])
    wb.save(str(path))
    return path


def _decompose(workbook: Path):
    df = pd.read_excel(workbook, sheet_name="Leave")
    norm = LeaveNormalizer(df, {"valid_ids": {"E001", "E002", "E003"}})
    return norm.decompose()


def test_ambiguous_dates_read_day_first(tmp_path):
    result = _decompose(_workbook(tmp_path / "leave.xlsx"))
    recs = result.entities["leave_records"]
    e001 = recs[recs["id_no"] == "E001"].iloc[0]
    assert e001["start_date"] == date(2026, 5, 1)
    assert e001["end_date"] == date(2026, 5, 5)
    apps = result.entities["leave_applications"]
    app = apps[apps["id_no"] == "E001"].iloc[0]
    assert app["proposed_leave_date"] == date(2026, 5, 1)
    assert app["issuance_date"] == date(2026, 4, 28)


def test_iso_control_and_second_employee(tmp_path):
    result = _decompose(_workbook(tmp_path / "leave.xlsx"))
    recs = result.entities["leave_records"]
    e002 = recs[recs["id_no"] == "E002"].iloc[0]
    assert e002["start_date"] == date(2026, 6, 1)
    assert e002["end_date"] == date(2026, 6, 3)


def test_garbage_dates_produce_no_record_and_orphans_quarantined(tmp_path):
    result = _decompose(_workbook(tmp_path / "leave.xlsx"))
    recs = result.entities["leave_records"]
    assert "E003" not in set(recs["id_no"])
    assert "E999" not in set(recs["id_no"])
    assert any("uploade" in w.lower() or "quarantin" in w.lower() or "unknown" in w.lower()
               for w in result.warnings), result.warnings
