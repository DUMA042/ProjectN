"""
owl.nominal.processor
~~~~~~~~~~~~~~~~~~~~~
NominalProcessor — production-grade, row-level Nominal Roll ETL.

Architecture
------------
1. NominalSignatureChecker  – validates 9 column positions before any processing
2. LookupTableCache         – pre-loads all 6 lookup tables; handles auto-insert
3. NominalRowParser         – extracts and type-converts a single Excel row by index
4. NominalProcessor         – orchestrates the full file with per-row DB transactions,
                              history tracking, and a complete processing report
5. NominalProcessingReport  – structured summary of every row outcome

Column Index Map (0-based, authoritative per prompt):
  1  → full_name
  2  → sex
  3  → id_no
  11 → geographical_zone
  12 → gl (→ gl_id)
  14 → rank (→ rank_id)
  15 → department (→ department_id)
  17 → location (→ location_id)
  25 → employment_type (→ emp_type_id)
  26 → status (→ status_id)
  27 → remark
  28 → date_of_last_deployment
  16 → IGNORED (Unit)
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Optional

import pandas as pd
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from owl.load.database import get_session
from owl.load.models import (
    Department,
    Employee,
    EmployeeDepartmentHistory,
    EmployeeGLHistory,
    EmployeeLocationHistory,
    EmployeeRankHistory,
    EmploymentType,
    EmployeeStatus,
    GradeLevel,
    Location,
    Rank,
)
from owl.logger import get_logger
from owl.nominal.validator import NominalFileValidator, _parse_id_no, _is_blank_id

log = get_logger(__name__)


# ── Column Index Constants ────────────────────────────────────────────────────

class ColIdx:
    SERIAL = 0       # IGNORE
    NAME = 1
    SEX = 2
    ID_NO = 3
    DOB = 4          # IGNORE
    QUALS = 5        # IGNORE
    PROF_BODIES = 6  # IGNORE
    PROF_QUALS = 7   # IGNORE
    CADRE = 8        # IGNORE
    STATE = 9        # IGNORE
    LGA = 10         # IGNORE
    GEO_ZONE = 11
    GL = 12
    STEP = 13        # IGNORE
    RANK = 14
    DEPARTMENT = 15
    UNIT = 16        # IGNORE — column removed from employees
    LOCATION = 17
    DATE_FIRST_APPT = 18  # IGNORE
    DATE_PRESENT_APPT = 19  # IGNORE
    DATE_LAST_INC = 20    # IGNORE
    DATE_PREV_INC = 21    # IGNORE
    INC_CUTOFF = 22       # IGNORE
    INC_COUNT = 23        # IGNORE
    APPLIED_INC = 24      # IGNORE
    EMP_TYPE = 25
    STATUS = 26
    REMARK = 27
    DEPLOYMENT_DATE = 28
    RESIDENTIAL_ADDR = 29  # IGNORE
    RESIDENTIAL_STATE = 30  # IGNORE


# ── Outcome types ─────────────────────────────────────────────────────────────

@dataclass
class RowOutcome:
    """Outcome for a single processed row."""
    row_number: int             # 1-indexed (Excel row number)
    id_no: Optional[str]
    status: str                 # "SUCCESS" | "PARTIAL_SUCCESS" | "FAILURE"
    action: Optional[str] = None  # "INSERT" | "UPDATE"
    warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class NominalProcessingReport:
    """Full summary of a Nominal Roll file processing run."""
    filename: str
    processed_at: datetime = field(default_factory=datetime.now)
    total_rows_read: int = 0
    total_new_inserts: int = 0
    total_updates: int = 0
    history_writes: dict[str, int] = field(default_factory=lambda: {
        "employee_department_history": 0,
        "employee_gl_history": 0,
        "employee_location_history": 0,
        "employee_rank_history": 0,
    })
    new_lookup_values: dict[str, list[str]] = field(default_factory=lambda: {
        "departments": [],
        "grade_levels": [],
        "locations": [],
        "ranks": [],
        "employee_statuses": [],
    })
    total_successes: int = 0
    total_partial_successes: int = 0
    total_failures: int = 0
    failed_id_nos: list[dict] = field(default_factory=list)
    row_outcomes: list[RowOutcome] = field(default_factory=list)

    def as_dict(self) -> dict:
        """Serialise to a JSON-compatible dict for storage in file_ingestion_meta."""
        return {
            "filename": self.filename,
            "processed_at": self.processed_at.isoformat(),
            "total_rows_read": self.total_rows_read,
            "total_new_inserts": self.total_new_inserts,
            "total_updates": self.total_updates,
            "history_writes": self.history_writes,
            "new_lookup_values": {k: v for k, v in self.new_lookup_values.items()},
            "total_successes": self.total_successes,
            "total_partial_successes": self.total_partial_successes,
            "total_failures": self.total_failures,
            "failed_id_nos": self.failed_id_nos,
        }

    def print_summary(self) -> None:
        """Print a human-readable summary to the logger."""
        log.info("=" * 60)
        log.info(f"NOMINAL ROLL PROCESSING SUMMARY")
        log.info(f"  File         : {self.filename}")
        log.info(f"  Processed at : {self.processed_at.strftime('%Y-%m-%d %H:%M:%S')}")
        log.info(f"  Total rows   : {self.total_rows_read}")
        log.info(f"  New inserts  : {self.total_new_inserts}")
        log.info(f"  Updates      : {self.total_updates}")
        log.info(f"  Successes    : {self.total_successes}")
        log.info(f"  Partial      : {self.total_partial_successes}")
        log.info(f"  Failures     : {self.total_failures}")
        log.info("  History writes:")
        for tbl, cnt in self.history_writes.items():
            log.info(f"    {tbl}: {cnt}")
        log.info("  New lookup values:")
        for tbl, vals in self.new_lookup_values.items():
            if vals:
                log.info(f"    {tbl}: {vals}")
        if self.failed_id_nos:
            log.warning("  Failed ID Nos:")
            for item in self.failed_id_nos:
                log.warning(f"    Row {item['row']}: id_no={item['id_no']} — {item['reason']}")
        log.info("=" * 60)


# ── Type conversion helpers ───────────────────────────────────────────────────

def _cell(row: pd.Series, idx: int) -> Any:
    """Safely get a cell from a Series by position index."""
    return row.iloc[idx] if idx < len(row) else None


def _to_str(value: Any) -> Optional[str]:
    """Convert cell to stripped string, None for blanks."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    s = str(value).strip()
    return s if s else None


def _to_date(value: Any) -> Optional[date]:
    """Convert Excel cell (serial, datetime, string) to a Python date.
    
    First pass: fast pd.to_datetime (vectorized internally, cached for repeated strings).
    Second pass: cached xlrd/dateutil fallback only for NaT results.
    """
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    # Fast path: pandas vectorized parser (covers most cases)
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            dt = pd.to_datetime(str(value).strip(), errors='coerce')
            if not pd.isna(dt):
                return dt.date()
    except Exception:
        pass

    # Slow path: xlrd / epoch / dateutil — cached to avoid repeated work
    return _fallback_parse_date(str(value).strip())


@lru_cache(maxsize=1024)
def _fallback_parse_date(raw: str) -> Optional[date]:
    """Cached slow-path date parser — handles Excel serials and ambiguous strings."""
    if not raw:
        return None

    # Try numeric (Excel serial)
    try:
        num = float(raw)
        if not math.isnan(num):
            import xlrd  # type: ignore
            return xlrd.xldate_as_datetime(int(num), 0).date()
    except (ValueError, ImportError):
        pass

    # Try epoch fallback
    try:
        num = int(float(raw))
        from datetime import timedelta
        base = date(1899, 12, 30)
        return base + timedelta(days=num)
    except (ValueError, OverflowError):
        pass

    # Try dateutil as last resort
    try:
        from dateutil.parser import parse as parse_dateutil
        return parse_dateutil(raw).date()
    except Exception:
        return None


def _to_date_from_series(series: pd.Series, idx: int) -> Optional[date]:
    """Extract a date from a pre-parsed Series, returning None for NaT/out-of-bounds."""
    if idx < 0 or idx >= len(series):
        return None
    val = series.iloc[idx]
    if pd.isna(val):
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    return None


def _to_id_no(value: Any) -> Optional[str]:
    """Convert id_no cell (int/float/str) to canonical string."""
    if _is_blank_id(value):
        return None
    s = str(value).strip()
    try:
        return str(int(float(s)))
    except (ValueError, TypeError):
        return s


def _to_lookup_key(value: Any) -> Optional[str]:
    """Normalise a lookup value for dictionary comparison (lowercase, stripped)."""
    v = _to_str(value)
    return v.lower() if v else None


# ── LookupTableCache ─────────────────────────────────────────────────────────

class LookupTableCache:
    """Pre-loads all 6 lookup tables and handles auto-insert for permitted tables.

    Auto-insert permitted: departments, grade_levels, locations, ranks, employee_statuses, employment_types
    """

    def __init__(self, session) -> None:
        self._session = session
        # {lower_name: id}
        self.departments: dict[str, int] = {}
        self.grade_levels: dict[str, int] = {}
        self.locations: dict[str, int] = {}
        self.ranks: dict[str, int] = {}
        self.statuses: dict[str, int] = {}
        self.emp_types: dict[str, int] = {}

    def load_all(self) -> None:
        """Load all lookup tables from the database into memory."""
        self.departments = self._load(Department, "department_name", "department_id")
        self.grade_levels = self._load(GradeLevel, "gl_name", "gl_id")
        self.locations = self._load(Location, "location_name", "location_id")
        self.ranks = self._load(Rank, "rank_name", "rank_id")
        self.statuses = self._load(EmployeeStatus, "status_name", "status_id")
        self.emp_types = self._load(EmploymentType, "emp_type_name", "emp_type_id")
        log.info(
            f"LookupTableCache loaded: "
            f"{len(self.departments)} depts, {len(self.grade_levels)} GLs, "
            f"{len(self.locations)} locations, {len(self.ranks)} ranks, "
            f"{len(self.statuses)} statuses, {len(self.emp_types)} emp_types"
        )

    def _load(self, model_class, name_col: str, id_col: str) -> dict[str, int]:
        rows = self._session.execute(select(model_class)).scalars().all()
        return {getattr(r, name_col).strip().lower(): getattr(r, id_col) for r in rows}

    def get_or_insert_dept(self, name: str, report: NominalProcessingReport) -> int:
        return self._get_or_insert(name, self.departments, Department, "department_name",
                                   "department_id", report, "departments")

    def get_or_insert_gl(self, name: str, report: NominalProcessingReport) -> int:
        return self._get_or_insert(name, self.grade_levels, GradeLevel, "gl_name",
                                   "gl_id", report, "grade_levels")

    def get_or_insert_location(self, name: str, report: NominalProcessingReport) -> int:
        return self._get_or_insert(name, self.locations, Location, "location_name",
                                   "location_id", report, "locations")

    def get_or_insert_rank(self, name: str, report: NominalProcessingReport) -> int:
        return self._get_or_insert(name, self.ranks, Rank, "rank_name",
                                   "rank_id", report, "ranks")

    def get_or_insert_status(self, name: str, report: NominalProcessingReport) -> int:
        return self._get_or_insert(name, self.statuses, EmployeeStatus, "status_name",
                                   "status_id", report, "employee_statuses")

    def _get_or_insert(
        self,
        name: str,
        cache: dict,
        model_class,
        name_attr: str,
        id_attr: str,
        report: NominalProcessingReport,
        table_label: str,
    ) -> int:
        key = name.strip().lower()
        if key in cache:
            return cache[key]
        # Auto-insert new value
        obj = model_class(**{name_attr: name.strip()})
        self._session.add(obj)
        self._session.flush()  # Populate the serial PK
        new_id = getattr(obj, id_attr)
        cache[key] = new_id
        report.new_lookup_values[table_label].append(name.strip())
        log.info(f"[LOOKUP AUTO-INSERT] {table_label}: '{name.strip()}' → id={new_id}")
        return new_id

    def get_or_insert_emp_type(self, name: str, report: NominalProcessingReport) -> int:
        return self._get_or_insert(name, self.emp_types, EmploymentType, "emp_type_name",
                                   "emp_type_id", report, "employment_types")


# ── NominalProcessor ─────────────────────────────────────────────────────────

class NominalProcessor:
    """
    Production-grade processor for the Nominal Roll Excel file.

    Each data row is processed inside its own database transaction.
    History tables are updated atomically with the employees table.

    Usage
    -----
    >>> processor = NominalProcessor(file_path="path/to/file.xlsx")
    >>> report = processor.process()
    >>> report.print_summary()
    """

    def __init__(self, file_path: str | Path) -> None:
        self._file_path = Path(file_path)

    def process(self, progress_callback: Callable[[str, int, int], None] | None = None) -> dict:
        """Run the full Nominal Roll processing pipeline.

        Parameters
        ----------
        progress_callback:
            Optional callback(stage, current, total) for SSE progress streaming.
            Called once per row with stage="row".

        Returns
        -------
        dict
            JSON-serialisable summary compatible with file_ingestion_meta.error_context.
        """
        report = NominalProcessingReport(filename=self._file_path.name)

        # ── Stage 1: Validate the file ────────────────────────────────────────
        validator = NominalFileValidator(self._file_path)
        val_result = validator.validate()
        if not val_result.valid:
            for err in val_result.errors:
                log.error(f"[VALIDATION FAILED] {err}")
            report.total_failures = 1
            report.failed_id_nos.append({"row": 0, "id_no": "N/A", "reason": "; ".join(val_result.errors)})
            report.print_summary()
            return report.as_dict()

        # ── Stage 2: Read the file (header = row 0) ───────────────────────────
        try:
            df_raw = pd.read_excel(self._file_path, header=None)
        except Exception as exc:
            log.error(f"Cannot read Excel file: {exc}")
            report.total_failures = 1
            report.failed_id_nos.append({"row": 0, "id_no": "N/A", "reason": str(exc)})
            return report.as_dict()

        # Data rows start at index 1 (row 0 is the header)
        data_rows = df_raw.iloc[1:].reset_index(drop=True)
        report.total_rows_read = len(data_rows)
        log.info(f"Processing {report.total_rows_read} data rows from '{self._file_path.name}'")

        # ── Pre-parse deployment dates (vectorized, avoids per-row try/except) ──
        deploy_raw = data_rows.iloc[:, ColIdx.DEPLOYMENT_DATE]
        deploy_dates = pd.to_datetime(deploy_raw, errors='coerce')
        nat_mask = deploy_dates.isna() & deploy_raw.notna()
        if nat_mask.any():
            for idx in deploy_dates.index[nat_mask]:
                deploy_dates.iloc[idx] = _fallback_parse_date(str(deploy_raw.iloc[idx]).strip())

        # ── Stage 3: Pre-load lookup tables and process each row ─────────────
        with get_session() as session:
            cache = LookupTableCache(session)
            cache.load_all()

            for local_idx, row in data_rows.iterrows():
                # Excel row number = 2 + local_idx (1-indexed, accounting for header)
                excel_row_num = local_idx + 2
                outcome = self._process_single_row(
                    row=row,
                    excel_row_num=excel_row_num,
                    session=session,
                    cache=cache,
                    report=report,
                    pre_parsed_deploy_date=_to_date_from_series(deploy_dates, local_idx),
                )
                report.row_outcomes.append(outcome)

                if progress_callback and (local_idx % 50 == 0 or local_idx == report.total_rows_read - 1):
                    progress_callback("row", local_idx + 1, report.total_rows_read)

                if outcome.status == "SUCCESS":
                    report.total_successes += 1
                elif outcome.status == "PARTIAL_SUCCESS":
                    report.total_partial_successes += 1
                else:
                    report.total_failures += 1
                    report.failed_id_nos.append({
                        "row": excel_row_num,
                        "id_no": outcome.id_no or "UNKNOWN",
                        "reason": outcome.error or "Unknown error",
                    })

        report.print_summary()
        self._write_summary_report(report)
        return report.as_dict()

    def _process_single_row(
        self,
        row: pd.Series,
        excel_row_num: int,
        session,
        cache: LookupTableCache,
        report: NominalProcessingReport,
        pre_parsed_deploy_date: Optional[date] = None,
    ) -> RowOutcome:
        """Process one Excel data row inside a savepoint transaction.

        Returns a RowOutcome with the result of the operation.
        """
        outcome = RowOutcome(row_number=excel_row_num, id_no=None, status="FAILURE")

        # ── Step 1: Parse id_no ───────────────────────────────────────────────
        raw_id = _cell(row, ColIdx.ID_NO)
        id_no = _to_id_no(raw_id)
        outcome.id_no = id_no

        if not id_no:
            outcome.error = "id_no is blank"
            log.error(f"Row {excel_row_num}: FAILURE — id_no is blank")
            return outcome

        # ── Step 2: Parse raw field values ────────────────────────────────────
        full_name = _to_str(_cell(row, ColIdx.NAME)) or ""
        sex = _to_str(_cell(row, ColIdx.SEX))
        geo_zone = _to_str(_cell(row, ColIdx.GEO_ZONE))
        gl_raw = _to_str(_cell(row, ColIdx.GL))
        rank_raw = _to_str(_cell(row, ColIdx.RANK))
        dept_raw = _to_str(_cell(row, ColIdx.DEPARTMENT))
        location_raw = _to_str(_cell(row, ColIdx.LOCATION))
        emp_type_raw = _to_str(_cell(row, ColIdx.EMP_TYPE))
        status_raw = _to_str(_cell(row, ColIdx.STATUS))
        remark_raw = _to_str(_cell(row, ColIdx.REMARK))
        remark = remark_raw if remark_raw and remark_raw.strip() else None
        deploy_date = pre_parsed_deploy_date
        deploy_date_raw = _cell(row, ColIdx.DEPLOYMENT_DATE)

        # ── Step 3: Validate sex ──────────────────────────────────────────────
        if sex and sex.upper() not in ("M", "F"):
            outcome.warnings.append(f"sex value '{sex}' is not M or F — stored as-is")
            log.warning(f"Row {excel_row_num}: sex='{sex}' is not M or F")

        # ── Step 4: Date-of-deployment quality check ──────────────────────────
        if deploy_date_raw is not None and not _is_blank_id(deploy_date_raw) and deploy_date is None:
            outcome.warnings.append(
                f"date_of_last_deployment '{deploy_date_raw}' could not be parsed — stored as NULL"
            )
            log.warning(f"Row {excel_row_num}: date_of_last_deployment '{deploy_date_raw}' unparseable")

        # ── Step 5: Resolve employment type (auto-insert if new) ──────────
        emp_type_id = cache.get_or_insert_emp_type(emp_type_raw, report) if emp_type_raw else None

        # ── Step 6: Resolve auto-insert lookup IDs ────────────────────────────
        try:
            dept_id = cache.get_or_insert_dept(dept_raw, report) if dept_raw else None
            gl_id = cache.get_or_insert_gl(gl_raw, report) if gl_raw else None
            location_id = cache.get_or_insert_location(location_raw, report) if location_raw else None
            rank_id = cache.get_or_insert_rank(rank_raw, report) if rank_raw else None
            status_id = cache.get_or_insert_status(status_raw, report) if status_raw else None
        except Exception as exc:
            outcome.error = f"Lookup resolution failed: {exc}"
            log.error(f"Row {excel_row_num}: FAILURE — {outcome.error}")
            return outcome

        # ── Step 7: Upsert inside a savepoint (atomic per row) ────────────────
        try:
            with session.begin_nested():
                existing = session.get(Employee, id_no)

                if existing is None:
                    # ── INSERT (new employee) ─────────────────────────────────
                    new_emp = Employee(
                        id_no=id_no,
                        full_name=full_name,
                        sex=sex,
                        department_id=dept_id,
                        gl_id=gl_id,
                        location_id=location_id,
                        rank_id=rank_id,
                        emp_type_id=emp_type_id,
                        status_id=status_id,
                        geographical_zone=geo_zone,
                        date_of_last_deployment=deploy_date,
                        phone_number=None,
                        remark=remark,
                    )
                    session.add(new_emp)
                    outcome.action = "INSERT"
                    report.total_new_inserts += 1
                    log.info(f"Row {excel_row_num}: INSERT id_no={id_no} name='{full_name}'")

                else:
                    # ── UPDATE (existing employee) ────────────────────────────
                    today = date.today()

                    # Check each tracked field for changes → write history
                    if dept_id is not None and existing.department_id != dept_id:
                        if existing.department_id is not None:
                            hist = EmployeeDepartmentHistory(
                                id_no=id_no,
                                department_id=existing.department_id,
                                start_date=self._get_history_start(session, "employee_department_history", id_no),
                                end_date=today,
                            )
                            session.add(hist)
                            report.history_writes["employee_department_history"] += 1
                        existing.department_id = dept_id

                    if gl_id is not None and existing.gl_id != gl_id:
                        if existing.gl_id is not None:
                            hist = EmployeeGLHistory(
                                id_no=id_no,
                                gl_id=existing.gl_id,
                                start_date=self._get_history_start(session, "employee_gl_history", id_no),
                                end_date=today,
                            )
                            session.add(hist)
                            report.history_writes["employee_gl_history"] += 1
                        existing.gl_id = gl_id

                    if location_id is not None and existing.location_id != location_id:
                        if existing.location_id is not None:
                            hist = EmployeeLocationHistory(
                                id_no=id_no,
                                location_id=existing.location_id,
                                start_date=self._get_history_start(session, "employee_location_history", id_no),
                                end_date=today,
                            )
                            session.add(hist)
                            report.history_writes["employee_location_history"] += 1
                        existing.location_id = location_id

                    if rank_id is not None and existing.rank_id != rank_id:
                        if existing.rank_id is not None:
                            hist = EmployeeRankHistory(
                                id_no=id_no,
                                rank_id=existing.rank_id,
                                start_date=self._get_history_start(session, "employee_rank_history", id_no),
                                end_date=today,
                            )
                            session.add(hist)
                            report.history_writes["employee_rank_history"] += 1
                        existing.rank_id = rank_id

                    # Non-tracked fields: update directly
                    existing.full_name = full_name
                    if sex:
                        existing.sex = sex
                    if status_id is not None:
                        existing.status_id = status_id
                    if emp_type_id is not None:
                        existing.emp_type_id = emp_type_id
                    if geo_zone:
                        existing.geographical_zone = geo_zone
                    if deploy_date:
                        existing.date_of_last_deployment = deploy_date
                    existing.remark = remark

                    outcome.action = "UPDATE"
                    report.total_updates += 1
                    log.info(f"Row {excel_row_num}: UPDATE id_no={id_no}")

        except Exception as exc:
            outcome.error = f"Transaction failed: {exc}"
            outcome.status = "FAILURE"
            log.error(f"Row {excel_row_num}: FAILURE — {outcome.error}")
            return outcome

        # ── Step 8: Determine final status ────────────────────────────────────
        if outcome.warnings:
            outcome.status = "PARTIAL_SUCCESS"
        else:
            outcome.status = "SUCCESS"

        return outcome

    @staticmethod
    def _get_history_start(session, table_name: str, id_no: str) -> date:
        """Get the start_date for a history record.

        Looks for an existing open history row (end_date IS NULL).
        Falls back to today if no open record exists.
        """
        result = session.execute(
            text(
                f"SELECT start_date FROM {table_name} "
                f"WHERE id_no = :id_no AND end_date IS NULL "
                f"ORDER BY start_date DESC LIMIT 1"
            ),
            {"id_no": id_no},
        ).fetchone()
        if result:
            return result[0]
        return date.today()

    def _write_summary_report(self, report: NominalProcessingReport) -> None:
        """Write a human-readable summary report to the reports/ directory."""
        try:
            reports_dir = Path("reports")
            reports_dir.mkdir(exist_ok=True)
            timestamp = report.processed_at.strftime("%Y%m%d_%H%M%S")
            report_path = reports_dir / f"nominal_report_{timestamp}.json"
            with open(report_path, "w", encoding="utf-8") as fh:
                json.dump(report.as_dict(), fh, indent=2, default=str)
            log.info(f"Summary report saved: {report_path}")
        except Exception as exc:
            log.warning(f"Could not write summary report: {exc}")
