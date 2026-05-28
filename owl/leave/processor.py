"""
owl.leave.processor
~~~~~~~~~~~~~~~~~~~
Dedicated processing engine for Leave Excel files.
Bypasses generic normalizer to maintain exact column positions for duplicate headers.
"""

from __future__ import annotations

import json
from datetime import datetime, date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from dateutil.parser import parse as parse_date
import holidays

from owl.load.database import get_session
from owl.load.models import LeaveApplication, LeaveRecord, LeaveType, Employee
from owl.logger import get_logger

log = get_logger(__name__)

# Required leave types for lookup
REQUIRED_LEAVE_TYPES = [
    "PRE-RETIREMENT LEAVE",
    "ANNUAL",
    "CASUAL AFTER ANNUAL",
    "COMPASSIONATE",
    "PATERNITY",
    "MATERNITY",
    "SICK",
    "EXAM",
]

# ── Shared Leave Signature Definitions ──────────────────────────────────────
LEAVE_MAJOR_SIGNATURES = {
    8: "PRE-RETIREMENTLEAVE",
    10: "CASUALBEFOREANNUAL", 
    22: "COMPASSIONATELEAVE",
    24: "PATERNITYLEAVE",
}

LEAVE_SUB_SIGNATURES = {
    2: "STAFFID",
    6: "PROPOSEDLEAVEDATE",
    7: "RESUMPTIONDATE",
}

def _check_leave_signatures(r1: pd.Series, r2: pd.Series) -> bool:
    """Validate Leave file header signatures (shared between classifier and processor).
    
    NOTE: Uses .iloc[] for positional access to be compatible with pandas 3.0+
    """
    def check(val, expected) -> bool:
        return str(val).strip().upper().replace(" ", "") == str(expected).upper().replace(" ", "")
    
    # ✅ FIX: Use .iloc[] for positional access (pandas 3.0+ compatibility)
    major_ok = all(check(r1.iloc[col], val) for col, val in LEAVE_MAJOR_SIGNATURES.items())
    sub_ok = all(check(r2.iloc[col], val) for col, val in LEAVE_SUB_SIGNATURES.items())
    return major_ok and sub_ok


class LeaveProcessor:
    """Processes Leave Excel files matching 0-indexed column signatures."""

    def __init__(self, file_path: str | Path) -> None:
        self.file_path = Path(file_path)
        self.ng_holidays = holidays.Nigeria()
        self.leave_types_dict: dict[str, int] = {}
        self.valid_employees: set[str] = set()

        self.summary = {
            "total_rows_read": 0,
            "total_leave_entries_attempted": 0,
            "total_leave_entries_inserted": 0,
            "warnings": [],
            "failures": [],
            "failed_staff_ids": [],
        }

    def _load_leave_types(self) -> None:
        """Load leave types from DB and ensure all required types exist."""
        with get_session() as session:
            db_types = session.query(LeaveType).all()
            for lt in db_types:
                norm_name = lt.leave_type_name.strip().lower().replace(" ", "")
                self.leave_types_dict[norm_name] = lt.leave_type_id

            for req in REQUIRED_LEAVE_TYPES:
                norm_req = req.strip().lower().replace(" ", "")
                if norm_req not in self.leave_types_dict:
                    raise RuntimeError(f"Configuration Error: Missing required leave type in database: '{req}'")

            emps = session.query(Employee.id_no).all()
            self.valid_employees = {e[0] for e in emps}

    def _get_type_id(self, type_name: str) -> int:
        norm_name = type_name.strip().lower().replace(" ", "")
        return self.leave_types_dict[norm_name]

    def _parse_date_cell(self, cell_val: Any) -> tuple[date | None, str | None]:
        """Attempt to parse date. Return (date_obj, raw_string_if_failed)."""
        if pd.isna(cell_val) or cell_val == "" or str(cell_val).strip() == "" or str(cell_val).lower() == "nan":
            return None, None
            
        if isinstance(cell_val, (datetime, pd.Timestamp)):
            return cell_val.date(), None
        if isinstance(cell_val, date):
            return cell_val, None

        str_val = str(cell_val).strip()
        try:
            parsed = parse_date(str_val, dayfirst=True)
            return parsed.date(), None
        except Exception:
            return None, str_val

    def process(self) -> dict:
        """Main execution flow for leave processing."""
        log.info(f"Starting LeaveProcessor for: {self.file_path}")
        self._load_leave_types()

        df_raw = pd.read_excel(self.file_path, header=None)
        header_idx = self._find_header_row(df_raw)
        
        if header_idx is None:
            raise ValueError("Could not find valid leave file headers.")

        data_start_idx = header_idx + 2  # Skips Major + Sub headers (Excel Row 1 & 2)
        
        with get_session() as session:
            for idx in range(data_start_idx, len(df_raw)):
                row = df_raw.iloc[idx]
                self.summary["total_rows_read"] += 1
                self._process_row(idx, row, session)
            
            session.commit()
            
        self._dump_report()
        
        # ✅ FIX: Return format expected by worker._mark_completed()
        # Worker expects: {table_name: {"success": int, "failed": int}}
        return {
            "LeaveApplication": {
                "success": self.summary["total_leave_entries_inserted"],
                "failed": len(self.summary["failures"])
            }
        }

    def _find_header_row(self, df_raw: pd.DataFrame) -> int | None:
        """Assume Excel Row 1 = Major Header, Row 2 = Sub-Header.

        Returns 0 (pandas index) if the file has at least 3 rows.
        Signature validation is kept for logging but won't block ingestion.
        
        NOTE: Uses .iloc[] for positional access to be compatible with pandas 3.0+
        """
        if len(df_raw) < 3:
            log.warning("Leave file has fewer than 3 rows. Cannot process.")
            return None

        r1 = df_raw.iloc[0]  # Excel Row 1 (Major Header)
        r2 = df_raw.iloc[1]  # Excel Row 2 (Sub-Header)

        def check(val, expected) -> bool:
            return str(val).strip().upper().replace(" ", "") == str(expected).upper().replace(" ", "")

        # ✅ FIX: Use .iloc[] for positional access (pandas 3.0+ compatibility)
        major_checks = [
            check(r1.iloc[8], "PRE-RETIREMENTLEAVE"),
            check(r1.iloc[10], "CASUALBEFOREANNUAL"),
            check(r1.iloc[22], "COMPASSIONATELEAVE"),
            check(r1.iloc[24], "PATERNITYLEAVE"),
        ]
        sub_checks = [
            check(r2.iloc[2], "STAFFID"),
            check(r2.iloc[6], "PROPOSEDLEAVEDATE"),
            check(r2.iloc[7], "RESUMPTIONDATE"),
        ]

        if all(major_checks) and all(sub_checks):
            log.info("Leave file validated: Excel Row 1 (Major) & Row 2 (Sub) match signatures.")
        else:
            log.warning(
                "Leave file signature mismatch detected. "
                "Proceeding anyway as requested (assuming Excel Row 1 = Major, Row 2 = Sub). "
                "Check file template if data extraction fails later."
            )
            # Log actual values for debugging
            log.debug(f"Row 1 values at signature cols: {r1.iloc[[8,10,22,24]].tolist()}")
            log.debug(f"Row 2 values at signature cols: {r2.iloc[[2,6,7]].tolist()}")

        # Always return 0 so ingestion continues
        return 0

    def _process_row(self, row_idx: int, row: pd.Series, session: Any) -> None:
        # ✅ FIX: Use .iloc[] for all positional accesses (pandas 3.0+ compatibility)
        staff_id = str(row.iloc[2]).strip()
        if not staff_id or staff_id == "nan":
            self._add_failure("MISSING_STAFF_ID", f"Row {row_idx}: No staff ID found.", staff_id)
            return

        if staff_id not in self.valid_employees:
            self._add_failure("INVALID_STAFF_ID", f"Row {row_idx}: Staff ID '{staff_id}' not found in database.", staff_id)
            return

        prop_date, prop_raw = self._parse_date_cell(row.iloc[6])
        resum_date, resum_raw = self._parse_date_cell(row.iloc[7])

        if prop_raw:
            self._add_warning("UNPARSEABLE_PROPOSED_DATE", f"Row {row_idx}: Proposed date '{prop_raw}' is a string.", staff_id)
        if resum_raw:
            self._add_warning("UNPARSEABLE_RESUMPTION_DATE", f"Row {row_idx}: Resumption date '{resum_raw}' is a string.", staff_id)

        remark = str(row.iloc[37]).strip()
        if remark == "nan" or not remark:
            remark = None

        leave_entries_to_insert = []
        
        # Helper to process standard leave chunks
        def extract_leave(start_col, end_col, type_name):
            start_d, start_r = self._parse_date_cell(row.iloc[start_col])
            end_d, end_r = self._parse_date_cell(row.iloc[end_col])
            
            if start_d is None and start_r is None and end_d is None and end_r is None:
                return # completely empty, skip silently
            
            self.summary["total_leave_entries_attempted"] += 1
            
            if (start_d is None and start_r is None) or (end_d is None and end_r is None):
                self._add_warning("MISSING_DATE_BOUND", f"Row {row_idx}: {type_name} missing start or end date.", staff_id)
                return

            if start_r or end_r:
                self._add_warning("UNPARSEABLE_LEAVE_DATE", f"Row {row_idx}: {type_name} has unparseable date strings.", staff_id)
            
            leave_entries_to_insert.append({
                "type_id": self._get_type_id(type_name),
                "start_d": start_d,
                "start_r": start_r,
                "end_d": end_d,
                "end_r": end_r
            })

        # Pre-Retirement Leave
        extract_leave(8, 9, "PRE-RETIREMENT LEAVE")
        # Casual Before Annual -> Annual Leave
        extract_leave(11, 12, "ANNUAL")
        # Casual After Annual
        extract_leave(14, 15, "CASUAL AFTER ANNUAL")
        # Compassionate Leave
        extract_leave(22, 23, "COMPASSIONATE")
        # Paternity Leave
        extract_leave(25, 26, "PATERNITY")
        # Sick Leave
        extract_leave(29, 30, "SICK")
        # Exam Leave
        extract_leave(32, 33, "EXAM")

        # Standalone Start/End Date (Cols 19 & 20) -> Annual or Maternity
        s_start_d, s_start_r = self._parse_date_cell(row.iloc[19])
        s_end_d, s_end_r = self._parse_date_cell(row.iloc[20])
        
        if not (s_start_d is None and s_start_r is None and s_end_d is None and s_end_r is None):
            self.summary["total_leave_entries_attempted"] += 1
            if (s_start_d is None and s_start_r is None) or (s_end_d is None and s_end_r is None):
                self._add_warning("MISSING_DATE_BOUND", f"Row {row_idx}: Standalone leave missing start or end date.", staff_id)
            elif s_start_r or s_end_r:
                self._add_warning("UNPARSEABLE_LEAVE_DATE", f"Row {row_idx}: Standalone leave has unparseable date strings.", staff_id)
            elif s_start_d and s_end_d:
                # Both are valid dates, calculate business days
                try:
                    import datetime as dt
                    # np.busday_count end date is exclusive, so we add 1 day to end_date to make it inclusive
                    end_inclusive = s_end_d + dt.timedelta(days=1)
                    
                    # np.busday_count requires numpy datetime64 and list of holiday dates
                    start_np = np.datetime64(s_start_d)
                    end_np = np.datetime64(end_inclusive)
                    
                    # Generate list of holidays for the years involved
                    holiday_dates = list(holidays.Nigeria(years=[s_start_d.year, end_inclusive.year]).keys())
                    holidays_np = [np.datetime64(h) for h in holiday_dates]
                    
                    duration = np.busday_count(start_np, end_np, holidays=holidays_np)
                    
                    if duration <= 30:
                        type_name = "ANNUAL"
                    else:
                        type_name = "MATERNITY"
                        
                    leave_entries_to_insert.append({
                        "type_id": self._get_type_id(type_name),
                        "start_d": s_start_d,
                        "start_r": None,
                        "end_d": s_end_d,
                        "end_r": None
                    })
                except Exception as e:
                    self._add_warning("CALCULATION_ERROR", f"Row {row_idx}: Could not calculate duration - {str(e)}", staff_id)

        # Create the LeaveApplication (Staff Leave Snapshot)
        app = LeaveApplication(
            id_no=staff_id,
            proposed_leave_date=prop_date,
            proposed_leave_date_raw=prop_raw,
            resumption_date=resum_date,
            remark=remark
        )
        session.add(app)
        session.flush() # flush to get application_id

        # Insert leave records
        if not leave_entries_to_insert:
            # If no actual leaves were found but we have proposed dates, insert a NULL leave type record
            if prop_date or prop_raw or resum_date or resum_raw:
                rec = LeaveRecord(
                    application_id=app.application_id,
                    id_no=staff_id,
                    leave_type_id=None,
                    start_date=prop_date,
                    start_date_raw=prop_raw,
                    end_date=resum_date,
                    end_date_raw=resum_raw,
                    planned_start_date=prop_date if prop_date else None,
                    planned_start_date_raw=prop_raw if prop_raw else None,
                    planned_end_date=resum_date if resum_date else None,
                    planned_end_date_raw=resum_raw if resum_raw else None
                )
                session.add(rec)
                self.summary["total_leave_entries_inserted"] += 1
        else:
            # Find the entry with the latest start_date
            latest_entry = None
            latest_date = None
            
            for entry in leave_entries_to_insert:
                if entry["start_d"]:
                    if latest_date is None or entry["start_d"] > latest_date:
                        latest_date = entry["start_d"]
                        latest_entry = entry
            
            # If no valid start dates found, fallback to the first entry
            if latest_entry is None and leave_entries_to_insert:
                latest_entry = leave_entries_to_insert[0]

            for entry in leave_entries_to_insert:
                is_latest = (entry is latest_entry)
                rec = LeaveRecord(
                    application_id=app.application_id,
                    id_no=staff_id,
                    leave_type_id=entry["type_id"],
                    start_date=entry["start_d"],
                    start_date_raw=entry["start_r"],
                    end_date=entry["end_d"],
                    end_date_raw=entry["end_r"],
                    planned_start_date=prop_date if is_latest else None,
                    planned_start_date_raw=prop_raw if is_latest else None,
                    planned_end_date=resum_date if is_latest else None,
                    planned_end_date_raw=resum_raw if is_latest else None
                )
                session.add(rec)
                self.summary["total_leave_entries_inserted"] += 1

    def _add_warning(self, w_type: str, message: str, staff_id: str) -> None:
        self.summary["warnings"].append({"type": w_type, "message": message, "staff_id": staff_id})

    def _add_failure(self, f_type: str, message: str, staff_id: str) -> None:
        self.summary["failures"].append({"type": f_type, "message": message, "staff_id": staff_id})
        if staff_id and staff_id != "nan":
            self.summary["failed_staff_ids"].append(staff_id)

    def _dump_report(self) -> None:
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = reports_dir / f"leave_report_{timestamp}.json"
        
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(self.summary, f, indent=4)
        
        log.info(f"Leave summary report generated at {report_path}")