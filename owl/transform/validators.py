"""
owl.transform.validators
~~~~~~~~~~~~~~~~~~~~~~~~
Pydantic v2 validation models — the contract between Transform and Load.

Role in the pipeline
--------------------
After normalisation, every entity dict is passed through the corresponding
Pydantic model *before* hitting the database.  This ensures:
  * No malformed data reaches the ORM / SQLAlchemy layer.
  * Validation errors surface with field-level context (row, column, value).
  * Type coercions are deterministic and auditable.

Conventions
-----------
* All models use ``model_config = ConfigDict(strict=False)`` to allow pandas
  type coercions (e.g. numpy int64 → int).
* String fields are ``stripped`` via ``@field_validator``.
* All models expose a ``from_row(cls, row: dict) -> <Model>`` class method for
  convenient DataFrame-row validation.

Note
----
These are *base* / *shared* validators.  Sheet-specific validators live in
``sheets/<sheet_name>/normalizer.py`` or a dedicated ``validators.py`` in that
sheet's package.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, ClassVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


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


# ── Shared dimension validators ───────────────────────────────────────────────

class EmployeeRecord(OwlBaseRecord):
    """Staff Record — aligned with 'employees' table."""

    id_no: str                # Primary Key
    full_name: str
    department_id: Optional[int] = None
    rank_id: Optional[int] = None
    unit_id: Optional[int] = None
    gl_id: Optional[int] = None
    location_id: Optional[int] = None
    status_id: Optional[int] = None
    employment_type_id: Optional[int] = None

    @field_validator("id_no", "full_name", mode="before")
    @classmethod
    def _strip_strings(cls, v: Any) -> str:
        return str(v).strip()


class DateRecord(OwlBaseRecord):
    """Date dimension record — used in star-schema fact tables."""

    id: str
    calendar_date: date

    @field_validator("calendar_date", mode="before")
    @classmethod
    def _coerce_date(cls, v: Any) -> date:
        if isinstance(v, (date, datetime)):
            return v.date() if isinstance(v, datetime) else v
        return date.fromisoformat(str(v).strip())


class TrainingRecord(OwlBaseRecord):
    """Training record — aligned with 'employee_trainings' table."""

    id_no: str
    venue_id: Optional[int] = None
    consultant_id: Optional[int] = None
    location_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class CardSwipeRecord(OwlBaseRecord):
    """Card swipe record — aligned with 'employee_card_swipes' table."""

    id_no: str
    location_id: Optional[int] = None
    swipe_time: datetime


# ── Validation result wrapper ─────────────────────────────────────────────────

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
