"""IR v2 matrix: supported capabilities validate; abuse and caps reject."""
from __future__ import annotations

import pytest

from owl.ai.ir2 import IRValidationError, validate


def base(**over):
    ir = {"source": "attendance", "select": [{"field": "department"}]}
    ir.update(over)
    return ir


def test_simple_select_defaults():
    out = validate(base())
    assert out["source"] == "attendance" and out["limit"] == 100
    assert out["offset"] == 0 and out["distinct"] is False
    assert out["subqueries"] == [] and out["ctes"] == [] and out["window"] is None


def test_filters_and_or_not():
    ir = base(filters={"and": [
        {"field": "work_date", "operator": "BETWEEN", "value": ["2026-09-01", "2026-09-30"]},
        {"or": [
            {"field": "status", "operator": "=", "value": "absent"},
            {"not": {"field": "status", "operator": "=", "value": "leave"}},
        ]},
    ]})
    assert validate(ir)["filters"]["and"][1]["or"][1]["not"]["field"] == "status"


def test_in_like_null_distinct():
    ir = base(
        select=[{"field": "full_name"}],
        filters={"and": [
            {"field": "department", "operator": "IN", "value": ["AHRD", "Finance"]},
            {"field": "grade_level", "operator": "NOT IN", "value": ["X"]},
            {"field": "full_name", "operator": "LIKE", "value": "Ada%"},
            {"field": "phone_number", "operator": "IS NULL"},
        ]},
        distinct=True,
    )
    assert validate(ir)["distinct"] is True


def test_aggregates_group_having_sort_page():
    ir = base(
        select=[{"field": "department"},
                {"aggregate": "AVG", "field": "minutes_worked", "alias": "avg_min"},
                {"aggregate": "COUNT", "field": "*", "alias": "n"}],
        group_by=["department"],
        having={"field": "n", "operator": ">", "value": 5},
        order_by=[{"field": "avg_min", "direction": "DESC"}],
        limit=10, offset=20,
    )
    out = validate(ir)
    assert out["limit"] == 10 and out["offset"] == 20


def test_calculated_and_case():
    ir = base(select=[
        {"expression": {"op": "/", "args": [{"field": "minutes_worked"}, {"literal": 60}]}, "alias": "hours"},
        {"case": {"whens": [{"when": {"field": "status", "operator": "=", "value": "absent"}, "then": 1}],
                 "else": 0}, "alias": "is_absent"},
    ])
    assert validate(ir)["select"][1]["alias"] == "is_absent"


def test_explicit_joins():
    ir = {
        "source": "training",
        "select": [{"field": "full_name"}, {"field": "venue"}],
        "joins": [{"table": "venues", "type": "LEFT"}],
    }
    assert validate(ir)["joins"] == [{"table": "venues", "type": "LEFT"}]
    # Unapproved / duplicate / self / bad-type / too-many joins rejected.
    for bad_joins in (
        [{"table": "employee_trainings"}],
        [{"table": "attendance_daily"}],
        [{"table": "venues"}, {"table": "consultants"}, {"table": "departments"},
         {"table": "ranks"}, {"table": "locations"}],
        [{"table": "venues", "type": "FULL"}],
        [{"table": "venues"}, {"table": "venues"}],
    ):
        with pytest.raises(IRValidationError):
            validate(base(joins=bad_joins))


def test_gated_capabilities_rejected():
    gated = [
        {"subqueries": [{"source": "employees", "select": [{"field": "full_name"}]}]},
        {"ctes": [{"name": "x", "query": {"source": "employees", "select": [{"field": "full_name"}]}}]},
        {"window": {"function": "ROW_NUMBER", "partition_by": ["department"],
                     "order_by": [{"field": "full_name", "direction": "ASC"}], "alias": "rn"}},
    ]
    for extra in gated:
        with pytest.raises(IRValidationError):
            validate(base(**extra))


def test_rejections_no_escape_hatch():
    bad = [
        base(select=[]),
        base(select=[{"field": "password"}]),
        base(select=[{"field": "department", "sql": "1; DROP TABLE x"}]),
        base(select=[{"expression": {"op": "EVAL", "args": []}, "alias": "x"}]),
        base(filters={"field": "department", "operator": "=", "value": ["not", "scalar"]}),
        base(filters={"field": "minutes_worked", "operator": "LIKE", "value": "x%"}),
        base(select=[{"field": "department"}], group_by=["department"],
             order_by=[{"field": "nope", "direction": "DESC"}]),
        base(select=[{"field": "department"}, {"aggregate": "SUM", "field": "minutes_worked", "alias": "s"}],
             group_by=[]),
        base(limit=0), base(limit=201), base(offset=-1),
        base(select=[{"field": "department"}, {"aggregate": "SUM", "field": "department", "alias": "s"}]),
        base(joins=[{"table": "employee_trainings"}]),
        base(joins=[{"table": key} for key in ("venues", "consultants", "departments", "ranks", "locations")]),
        base(extra_key=1),
    ]
    for b in bad:
        with pytest.raises(IRValidationError):
            validate(b)


def test_hostile_values_validate_but_bind():
    """Attack strings are legal *values* — they must bind as params, never inline."""
    ir = base(filters={"field": "department", "operator": "=", "value": "'; DROP TABLE x;--"})
    out = validate(ir)
    assert out["filters"]["value"] == "'; DROP TABLE x;--"

