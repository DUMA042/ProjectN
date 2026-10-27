"""Roster editing: PATCH /api/employees/{id_no} and its validation.

Runs against the live development database (same as the other API tests) and
creates/removes a disposable employee so no real staff record is touched.
"""
from __future__ import annotations

import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from api import main as app_module
from owl.load.database import get_session

client = TestClient(app_module.app)

EMPLOYEE_ID = f"TST-EDIT-{uuid.uuid4().hex[:8]}"
HISTORY_TABLES = (
    "employee_department_history",
    "employee_rank_history",
    "employee_gl_history",
    "employee_location_history",
)


def _ids(sql: str) -> list[int]:
    with get_session() as session:
        return [row[0] for row in session.execute(text(sql))]


@pytest.fixture()
def employee():
    departments = _ids(
        "SELECT department_id FROM departments ORDER BY department_id LIMIT 2"
    )
    ranks = _ids("SELECT rank_id FROM ranks ORDER BY rank_id LIMIT 2")
    grade_levels = _ids("SELECT gl_id FROM grade_levels ORDER BY gl_id LIMIT 2")
    statuses = _ids("SELECT status_id FROM employee_statuses ORDER BY status_id LIMIT 2")
    emp_types = _ids("SELECT emp_type_id FROM employment_types ORDER BY emp_type_id LIMIT 2")
    if len(departments) < 2 or not ranks or not grade_levels or not statuses or not emp_types:
        pytest.skip("lookup tables are not populated")

    with get_session() as session:
        session.execute(
            text(
                "INSERT INTO employees "
                "(id_no, full_name, sex, department_id, rank_id, gl_id, status_id, emp_type_id) "
                "VALUES (:id_no, :name, 'M', :department_id, :rank_id, :gl_id, "
                ":status_id, :emp_type_id)"
            ),
            {
                "id_no": EMPLOYEE_ID,
                "name": "Edit Test",
                "department_id": departments[0],
                "rank_id": ranks[0],
                "gl_id": grade_levels[0],
                "status_id": statuses[0],
                "emp_type_id": emp_types[0],
            },
        )

    yield {
        "id_no": EMPLOYEE_ID,
        "departments": departments,
        "ranks": ranks,
        "grade_levels": grade_levels,
        "statuses": statuses,
    }

    with get_session() as session:
        for table in HISTORY_TABLES:
            session.execute(
                text(f"DELETE FROM {table} WHERE id_no = :id_no"), {"id_no": EMPLOYEE_ID}
            )
        session.execute(
            text("DELETE FROM employees WHERE id_no = :id_no"), {"id_no": EMPLOYEE_ID}
        )


def test_detail_exposes_lookup_ids(employee):
    res = client.get(f"/api/employees/{EMPLOYEE_ID}/detail")
    assert res.status_code == 200
    body = res.json()
    assert body["department_id"] == employee["departments"][0]
    assert body["rank_id"] == employee["ranks"][0]
    assert body["gl_id"] == employee["grade_levels"][0]
    assert body["emp_type_id"] is not None and body["status_id"] is not None


def test_lookups_endpoint_returns_options():
    res = client.get("/api/employees/lookups")
    assert res.status_code == 200
    body = res.json()
    for key in ("departments", "ranks", "grade_levels", "employment_types", "statuses"):
        assert body[key] and {"id", "name"} <= set(body[key][0])
    assert body["sexes"] == ["F", "M"]
    assert isinstance(body["zones"], list)


def test_update_scalar_fields(employee):
    res = client.patch(
        f"/api/employees/{EMPLOYEE_ID}",
        json={
            "full_name": "  Renamed Staff  ",
            "phone_number": "0801 234-5678",
            "sex": "f",
            "geographical_zone": "Lagos",
            "date_of_last_deployment": "2024-02-29",
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["full_name"] == "Renamed Staff"
    assert body["phone_number"] == "0801 234-5678"
    assert body["sex"] == "F"
    assert body["date_of_last_deployment"] == "2024-02-29"


def test_clear_optional_field(employee):
    res = client.patch(f"/api/employees/{EMPLOYEE_ID}", json={"phone_number": ""})
    assert res.status_code == 200
    assert res.json()["phone_number"] is None


def test_department_change_writes_history(employee):
    old_department = employee["departments"][0]
    res = client.patch(
        f"/api/employees/{EMPLOYEE_ID}",
        json={"department_id": employee["departments"][1]},
    )
    assert res.status_code == 200, res.text
    assert res.json()["department_id"] == employee["departments"][1]

    with get_session() as session:
        rows = session.execute(
            text(
                "SELECT department_id, end_date, start_date "
                "FROM employee_department_history WHERE id_no = :id_no"
            ),
            {"id_no": EMPLOYEE_ID},
        ).all()
    assert len(rows) == 1
    assert rows[0][0] == old_department
    assert rows[0][1] == date.today()
    assert rows[0][2] == date.today()


def test_rank_and_grade_history(employee):
    res = client.patch(
        f"/api/employees/{EMPLOYEE_ID}",
        json={"rank_id": employee["ranks"][1], "gl_id": employee["grade_levels"][1]},
    )
    assert res.status_code == 200, res.text

    with get_session() as session:
        rank_rows = session.execute(
            text("SELECT rank_id FROM employee_rank_history WHERE id_no = :id_no"),
            {"id_no": EMPLOYEE_ID},
        ).all()
        gl_rows = session.execute(
            text("SELECT gl_id FROM employee_gl_history WHERE id_no = :id_no"),
            {"id_no": EMPLOYEE_ID},
        ).all()
    assert [r[0] for r in rank_rows] == [employee["ranks"][0]]
    assert [r[0] for r in gl_rows] == [employee["grade_levels"][0]]


def test_id_cannot_be_edited(employee):
    res = client.patch(f"/api/employees/{EMPLOYEE_ID}", json={"id_no": "SOMEONE-ELSE"})
    assert res.status_code == 422


def test_unknown_foreign_key_is_rejected(employee):
    res = client.patch(
        f"/api/employees/{EMPLOYEE_ID}", json={"department_id": 999_999}
    )
    assert res.status_code == 422
    assert res.json()["detail"]["field"] == "department_id"


@pytest.mark.parametrize(
    "payload",
    [
        {"full_name": "   "},
        {"phone_number": "not-a-phone"},
        {"sex": "X"},
        {"date_of_last_deployment": "2999-01-01"},
        {"date_of_last_deployment": "not-a-date"},
        {"geographical_zone": "z" * 101},
        {"department_id": 0},
    ],
)
def test_invalid_values_are_rejected(employee, payload):
    res = client.patch(f"/api/employees/{EMPLOYEE_ID}", json=payload)
    assert res.status_code == 422


def test_unknown_employee_is_404():
    res = client.patch("/api/employees/NOPE-NOT-HERE", json={"full_name": "Ghost"})
    assert res.status_code == 404
