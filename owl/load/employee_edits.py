"""Manual roster edits from the desktop UI.

Mirrors nominal-roll behaviour: department, rank and grade-level changes close
the previous assignment in the matching history table before the new value is
applied.  ``id_no`` is deliberately not editable — nine tables reference it and
pre-generated reports embed it.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from owl.load.history import history_start

EDITABLE_FIELDS = (
    "full_name",
    "sex",
    "phone_number",
    "geographical_zone",
    "date_of_last_deployment",
    "department_id",
    "rank_id",
    "gl_id",
    "emp_type_id",
    "status_id",
)

FK_LOOKUPS: dict[str, tuple[str, str, str]] = {
    "department_id": ("departments", "department_id", "Department"),
    "rank_id": ("ranks", "rank_id", "Rank"),
    "gl_id": ("grade_levels", "gl_id", "Grade level"),
    "emp_type_id": ("employment_types", "emp_type_id", "Employment type"),
    "status_id": ("employee_statuses", "status_id", "Status"),
}

HISTORY_BY_FIELD: dict[str, tuple[str, str]] = {
    "department_id": ("employee_department_history", "department_id"),
    "rank_id": ("employee_rank_history", "rank_id"),
    "gl_id": ("employee_gl_history", "gl_id"),
}

SEX_VALUES = {"M", "F"}
_PHONE = re.compile(r"^[0-9+()\-\s]{3,30}$")


class EmployeeEditError(ValueError):
    """A validation problem tied to one field (mapped to HTTP 422)."""

    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field
        self.message = message


class EmployeeNotFound(LookupError):
    """No employee with the requested id_no (mapped to HTTP 404)."""


def _text_or_none(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _normalise(changes: dict[str, Any]) -> dict[str, Any]:
    unknown = sorted(set(changes) - set(EDITABLE_FIELDS))
    if unknown:
        raise EmployeeEditError(
            unknown[0], f"Field '{unknown[0]}' cannot be edited."
        )

    out: dict[str, Any] = {}
    for field, value in changes.items():
        if field == "full_name":
            name = _text_or_none(value)
            if not name:
                raise EmployeeEditError(field, "Full name is required.")
            if len(name) > 255:
                raise EmployeeEditError(field, "Full name must be 255 characters or fewer.")
            out[field] = name
        elif field == "sex":
            sex = _text_or_none(value)
            sex = sex.upper() if sex else None
            if sex is not None and sex not in SEX_VALUES:
                raise EmployeeEditError(field, "Sex must be M or F.")
            out[field] = sex
        elif field == "phone_number":
            phone = _text_or_none(value)
            if phone is not None and not _PHONE.match(phone):
                raise EmployeeEditError(
                    field, "Phone number may contain digits, spaces, +, -, ( ) only."
                )
            out[field] = phone
        elif field == "geographical_zone":
            zone = _text_or_none(value)
            if zone is not None and len(zone) > 100:
                raise EmployeeEditError(
                    field, "Geographical zone must be 100 characters or fewer."
                )
            out[field] = zone
        elif field == "date_of_last_deployment":
            if value in (None, ""):
                out[field] = None
                continue
            try:
                parsed = date.fromisoformat(str(value))
            except ValueError as exc:
                raise EmployeeEditError(
                    field, "Last deployment must be a date (YYYY-MM-DD)."
                ) from exc
            if parsed > date.today():
                raise EmployeeEditError(field, "Last deployment cannot be in the future.")
            out[field] = parsed
        else:
            if value in (None, ""):
                out[field] = None
                continue
            try:
                number = int(value)  # type: ignore[arg-type]
            except (TypeError, ValueError) as exc:
                raise EmployeeEditError(field, "Must be a valid selection.") from exc
            if number <= 0:
                raise EmployeeEditError(field, "Must be a valid selection.")
            out[field] = number
    return out


def _validate_lookups(session: Session, changes: dict[str, Any]) -> None:
    for field, (table, pk, label) in FK_LOOKUPS.items():
        if field not in changes or changes[field] is None:
            continue
        exists = session.execute(
            text(f"SELECT 1 FROM {table} WHERE {pk} = :value"),
            {"value": changes[field]},
        ).first()
        if not exists:
            raise EmployeeEditError(field, f"{label} does not exist.")


def apply_employee_update(
    session: Session, id_no: str, changes: dict[str, Any]
) -> dict[str, list[str]]:
    """Validate and apply an edit. Does not commit — the route owns the transaction."""
    normalised = _normalise(changes)

    current = session.execute(
        text(
            "SELECT department_id, rank_id, gl_id FROM employees WHERE id_no = :id_no"
        ),
        {"id_no": id_no},
    ).mappings().first()
    if current is None:
        raise EmployeeNotFound(id_no)

    _validate_lookups(session, normalised)

    today = date.today()
    history_written: list[str] = []
    for field, (table, column) in HISTORY_BY_FIELD.items():
        if field not in normalised:
            continue
        previous = current[field]
        if previous is None or previous == normalised[field]:
            continue
        session.execute(
            text(
                f"INSERT INTO {table} (id_no, {column}, start_date, end_date) "
                "VALUES (:id_no, :value, :start_date, :end_date)"
            ),
            {
                "id_no": id_no,
                "value": previous,
                "start_date": history_start(session, table, id_no),
                "end_date": today,
            },
        )
        history_written.append(table)

    if normalised:
        assignments = ", ".join(f"{field} = :{field}" for field in normalised)
        session.execute(
            text(f"UPDATE employees SET {assignments} WHERE id_no = :id_no"),
            {**normalised, "id_no": id_no},
        )

    return {"changed": sorted(normalised), "history_written": history_written}
