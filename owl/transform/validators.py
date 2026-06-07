"""
owl.transform.validators
~~~~~~~~~~~~~~~~~~~~~~~~
Pydantic v2 validation models — the contract between Transform and Load.

Role in the pipeline
--------------------
After normalisation, every entity DataFrame is passed through the corresponding
Pydantic model *before* hitting the database.  This ensures:
  * No malformed data reaches the ORM / SQLAlchemy layer.
  * Validation errors surface with field-level context (row, column, value).
  * Type coercions are deterministic and auditable.

Conventions
-----------
* All models use ``model_config = ConfigDict(strict=False)`` to allow pandas
  type coercions (e.g. numpy int64 → int).
* String fields are ``stripped`` via ``str_strip_whitespace=True``.
* All models expose a ``from_row(cls, row: dict) -> <Model>`` class method for
  convenient DataFrame-row validation.

Architecture
------------
Tables without a registered Pydantic model in ``VALIDATOR_MAP`` pass through
validation untouched — this makes the system opt-in and safe to extend
incrementally.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, ClassVar, Optional

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

import pandas as pd

from owl.logger import get_logger

log = get_logger(__name__)


# ── Base record ───────────────────────────────────────────────────────────────

class OwlBaseRecord(BaseModel):
    """Common base for all pipeline records.

    Provides:
    * Permissive coercion config (strict=False, arbitrary_types_allowed=True).
    * A ``from_row`` class method for validating a single dict / DataFrame row.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        strict=False,
        arbitrary_types_allowed=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "OwlBaseRecord":
        """Validate and coerce a dict (e.g. a DataFrame ``.to_dict()`` row).

        Parameters
        ----------
        row:
            Raw key-value mapping from a cleaned DataFrame row.

        Returns
        -------
        OwlBaseRecord
            Validated and coerced instance.

        Raises
        ------
        pydantic.ValidationError
            With field-level detail if validation fails.
        """
        return cls.model_validate(row)


# ═══════════════════════════════════════════════════════════════════════════════
# DIMENSION TABLE VALIDATORS
# ═══════════════════════════════════════════════════════════════════════════════

class UnitRecord(OwlBaseRecord):
    """Validates rows for the 'units' dimension table."""
    unit_id: int
    unit_name: str


class RankRecord(OwlBaseRecord):
    """Validates rows for the 'ranks' dimension table."""
    rank_id: int
    rank_name: str


class DepartmentRecord(OwlBaseRecord):
    """Validates rows for the 'departments' dimension table."""
    department_id: int
    department_name: str


class GradeLevelRecord(OwlBaseRecord):
    """Validates rows for the 'grade_levels' dimension table."""
    gl_id: int
    gl_name: str


class LocationRecord(OwlBaseRecord):
    """Validates rows for the 'locations' dimension table."""
    location_id: Optional[int] = None
    location_name: str


class VenueRecord(OwlBaseRecord):
    """Validates rows for the 'venues' dimension table."""
    venue_id: Optional[int] = None
    venue_name: str


class ConsultantRecord(OwlBaseRecord):
    """Validates rows for the 'consultants' dimension table."""
    consultant_id: Optional[int] = None
    consultant_name: str


class EmploymentTypeRecord(OwlBaseRecord):
    """Validates rows for the 'employment_types' dimension table."""
    emp_type_id: int
    emp_type_name: str


class EmployeeStatusRecord(OwlBaseRecord):
    """Validates rows for the 'employee_statuses' dimension table."""
    status_id: int
    status_name: str


class LeaveTypeRecord(OwlBaseRecord):
    """Validates rows for the 'leave_types' dimension table."""
    leave_type_id: int
    leave_type_name: str


# ═══════════════════════════════════════════════════════════════════════════════
# CORE ENTITY VALIDATORS
# ═══════════════════════════════════════════════════════════════════════════════

class EmployeeRecord(OwlBaseRecord):
    """Staff Record — aligned with 'employees' table."""

    id_no: str
    full_name: str
    sex: Optional[str] = None
    rank_id: Optional[int] = None
    department_id: Optional[int] = None
    gl_id: Optional[int] = None
    emp_type_id: Optional[int] = None
    status_id: Optional[int] = None
    location_id: Optional[int] = None
    geographical_zone: Optional[str] = None
    date_of_last_deployment: Optional[date] = None
    phone_number: Optional[str] = None
    remark: Optional[str] = None

    @field_validator("id_no", "full_name", mode="before")
    @classmethod
    def _strip_strings(cls, v: Any) -> str:
        return str(v).strip()

    @field_validator("date_of_last_deployment", mode="before")
    @classmethod
    def _coerce_deployment_date(cls, v: Any) -> date | None:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, date):
            return v
        try:
            return date.fromisoformat(str(v).strip())
        except (ValueError, TypeError):
            return None


class TrainingRecord(OwlBaseRecord):
    """Training record — aligned with 'employee_trainings' table."""

    id_no: str
    venue_id: Optional[int] = None
    consultant_id: Optional[int] = None
    location_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def _coerce_date(cls, v: Any) -> date | None:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, date):
            return v
        return date.fromisoformat(str(v).strip())


class CardSwipeRecord(OwlBaseRecord):
    """Card swipe record — aligned with 'employee_card_swipes' table."""

    id_no: str
    location_id: Optional[int] = None
    swipe_time: datetime

    @field_validator("swipe_time", mode="before")
    @classmethod
    def _coerce_swipe_time(cls, v: Any) -> datetime:
        if isinstance(v, datetime):
            return v
        if isinstance(v, date):
            return datetime(v.year, v.month, v.day)
        return pd.to_datetime(v)


class LeaveApplicationRecord(OwlBaseRecord):
    """Aligned with 'leave_applications' table."""
    application_id: Optional[int] = None
    id_no: str
    proposed_leave_date: Optional[date] = None
    proposed_leave_date_raw: Optional[str] = None
    resumption_date: Optional[date] = None
    forfeiture: Optional[str] = None
    issuance_date: Optional[date] = None
    issuance_date_raw: Optional[str] = None
    remark: Optional[str] = None

    @field_validator("proposed_leave_date", "resumption_date", "issuance_date", mode="before")
    @classmethod
    def _coerce_date(cls, v: Any) -> date | None:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, date):
            return v
        try:
            return date.fromisoformat(str(v).strip())
        except (ValueError, TypeError):
            return None

class LeaveRecordRecord(OwlBaseRecord):
    """Aligned with 'leave_records' table."""
    record_id: Optional[int] = None
    application_id: Optional[int] = None
    id_no: str
    leave_type_id: Optional[int] = None
    start_date: date
    end_date: Optional[date] = None

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def _coerce_date(cls, v: Any) -> date | None:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, date):
            return v
        try:
            return date.fromisoformat(str(v).strip())
        except (ValueError, TypeError):
            return None


# ═══════════════════════════════════════════════════════════════════════════════
# KANBAN TABLE VALIDATORS
# ═══════════════════════════════════════════════════════════════════════════════

class KanbanBoardRecord(OwlBaseRecord):
    board_id: Optional[int] = None
    board_name: str
    description: Optional[str] = None
    department_id: Optional[int] = None
    is_archived: bool = False

class KanbanColumnRecord(OwlBaseRecord):
    column_id: Optional[int] = None
    board_id: int
    column_name: str
    position: int = 0
    color: Optional[str] = None
    is_done_column: bool = False

class KanbanLabelRecord(OwlBaseRecord):
    label_id: Optional[int] = None
    label_name: str
    color: Optional[str] = None

class KanbanTaskRecord(OwlBaseRecord):
    task_id: Optional[int] = None
    board_id: int
    column_id: int
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    due_date: Optional[date] = None
    position: int = 0
    is_archived: bool = False

    @field_validator("due_date", mode="before")
    @classmethod
    def _coerce_date(cls, v: Any) -> date | None:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, date):
            return v
        return date.fromisoformat(str(v).strip())

class KanbanTaskAssigneeRecord(OwlBaseRecord):
    assignment_id: Optional[int] = None
    task_id: int
    id_no: Optional[str] = None
    assigned_by: Optional[str] = None

class KanbanTaskLabelRecord(OwlBaseRecord):
    task_id: int
    label_id: int

class KanbanTaskHistoryRecord(OwlBaseRecord):
    history_id: Optional[int] = None
    task_id: int
    from_column_id: Optional[int] = None
    to_column_id: int
    moved_by: Optional[str] = None
    duration_in_previous: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# QUARANTINE TABLE VALIDATORS
# ═══════════════════════════════════════════════════════════════════════════════

class QuarantineCardSwipeRecord(OwlBaseRecord):
    """Validates rows for the 'quarantine_card_swipes' table."""

    employee_name: Optional[str] = None
    location_name: Optional[str] = None
    swipe_time: datetime

    @field_validator("swipe_time", mode="before")
    @classmethod
    def _coerce_swipe_time(cls, v: Any) -> datetime:
        if isinstance(v, datetime):
            return v
        if isinstance(v, date):
            return datetime(v.year, v.month, v.day)
        return pd.to_datetime(v)


class QuarantineTrainingRecord(OwlBaseRecord):
    """Validates rows for the 'quarantine_trainings' table."""

    id_no: str
    venue_name: Optional[str] = None
    consultant_name: Optional[str] = None
    start_date: date
    end_date: date

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def _coerce_date(cls, v: Any) -> date:
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, date):
            return v
        return date.fromisoformat(str(v).strip())


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION RESULT WRAPPER
# ═══════════════════════════════════════════════════════════════════════════════

class ValidationReport(BaseModel):
    """Holds the outcome of validating a batch of rows."""

    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)

    valid_records: list[OwlBaseRecord] = []
    invalid_rows: list[dict[str, Any]] = []    # raw rows that failed
    errors: list[str] = []                     # human-readable error messages

    @property
    def success_rate(self) -> float:
        total = len(self.valid_records) + len(self.invalid_rows)
        return len(self.valid_records) / total if total else 0.0

    @property
    def has_errors(self) -> bool:
        return bool(self.invalid_rows)


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATOR MAP — Links table names to their Pydantic models
# ═══════════════════════════════════════════════════════════════════════════════

VALIDATOR_MAP: dict[str, type[OwlBaseRecord]] = {
    # Dimension tables
    "units": UnitRecord,
    "ranks": RankRecord,
    "departments": DepartmentRecord,
    "grade_levels": GradeLevelRecord,
    "locations": LocationRecord,
    "venues": VenueRecord,
    "consultants": ConsultantRecord,
    "employment_types": EmploymentTypeRecord,
    "employee_statuses": EmployeeStatusRecord,
    "leave_types": LeaveTypeRecord,
    # Core entities
    "employees": EmployeeRecord,
    "employee_trainings": TrainingRecord,
    "employee_card_swipes": CardSwipeRecord,
    "leave_applications": LeaveApplicationRecord,
    "leave_records": LeaveRecordRecord,
    # Kanban entities
    "kanban_boards": KanbanBoardRecord,
    "kanban_columns": KanbanColumnRecord,
    "kanban_labels": KanbanLabelRecord,
    "kanban_tasks": KanbanTaskRecord,
    "kanban_task_assignees": KanbanTaskAssigneeRecord,
    "kanban_task_labels": KanbanTaskLabelRecord,
    "kanban_task_history": KanbanTaskHistoryRecord,
    # Quarantine tables
    "quarantine_card_swipes": QuarantineCardSwipeRecord,
    "quarantine_trainings": QuarantineTrainingRecord,
}


# ═══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATION — validate_dataframe()
# ═══════════════════════════════════════════════════════════════════════════════

def validate_dataframe(
    table_name: str,
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Validate a DataFrame against the Pydantic model registered for *table_name*.

    Parameters
    ----------
    table_name:
        The target database table name (must match a key in ``VALIDATOR_MAP``).
    df:
        The entity DataFrame produced by the normalizer.

    Returns
    -------
    tuple[pd.DataFrame, list[dict]]
        - ``valid_df``: A new DataFrame containing only rows that passed validation.
        - ``errors``: A list of error dicts, each containing:
            - ``row_index``: The original row index from the DataFrame.
            - ``row_data``: The raw dict of the rejected row.
            - ``field``: The specific field that failed.
            - ``message``: Human-readable explanation of the failure.

    Notes
    -----
    If no model is registered for *table_name*, the DataFrame passes through
    **unmodified** and an empty error list is returned. This makes the
    validation layer opt-in and safe to extend incrementally.
    """
    model_class = VALIDATOR_MAP.get(table_name)

    if model_class is None:
        log.debug(f"No validator registered for table '{table_name}' — passing through.")
        return df, []

    if df.empty:
        return df, []

    log.info(f"Validating {len(df)} row(s) for table '{table_name}'...")

    valid_rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for idx, row in df.iterrows():
        row_dict = row.to_dict()

        # Clean NaN/NaT values to None for Pydantic
        def _to_none_if_null(v: Any) -> Any:
            """Convert pandas NaN, NaT, and None to Python None."""
            if v is None:
                return None
            if isinstance(v, str):
                return v
            try:
                if pd.isna(v):
                    return None
            except (ValueError, TypeError):
                pass
            return v

        cleaned_dict = {k: _to_none_if_null(v) for k, v in row_dict.items()}

        try:
            validated = model_class.from_row(cleaned_dict)
            valid_rows.append(validated.model_dump())
        except ValidationError as exc:
            for error in exc.errors():
                field_name = " → ".join(str(loc) for loc in error["loc"])
                error_detail = {
                    "row_index": idx,
                    "row_data": row_dict,
                    "field": field_name,
                    "message": f"Row {idx}, field '{field_name}': {error['msg']}",
                }
                errors.append(error_detail)
                log.warning(error_detail["message"])

    # Rebuild a clean DataFrame from validated rows
    if valid_rows:
        valid_df = pd.DataFrame(valid_rows)
    else:
        valid_df = pd.DataFrame(columns=df.columns)

    rejected_count = len(df) - len(valid_rows)
    if rejected_count > 0:
        log.warning(
            f"Validation for '{table_name}': {len(valid_rows)} passed, "
            f"{rejected_count} rejected ({len(errors)} error(s))."
        )
    else:
        log.info(f"Validation for '{table_name}': all {len(valid_rows)} row(s) passed.")

    return valid_df, errors
