"""Compiler tests: generic primitives produce single parameterized SELECTs."""
from __future__ import annotations

from owl.ai import compiler


def spec_example():
    return {
        "source": "attendance",
        "select": [
            {"field": "department"},
            {"aggregate": "AVG", "field": "minutes_worked", "alias": "average_late_minutes"},
        ],
        "filters": {"and": [
            {"field": "work_date", "operator": "BETWEEN", "value": ["2026-09-01", "2026-09-30"]},
            {"field": "employment_status", "operator": "=", "value": "Active"},
        ]},
        "group_by": ["department"],
        "order_by": [{"field": "average_late_minutes", "direction": "DESC"}],
        "limit": 10,
    }


def test_avg_time_compiles_to_epoch():
    from owl.ai import ir2, secure_execute
    from owl.ai import catalog as catalog_module

    ir = ir2.validate({
        "source": "attendance",
        "select": [
            {"field": "department"},
            {"aggregate": "AVG", "field": "checkin_time", "alias": "avg_checkin"},
        ],
        "group_by": ["department"],
        "order_by": [{"field": "avg_checkin", "direction": "ASC"}],
        "limit": 10,
    })
    sql, params, meta = compiler.compile(ir)
    assert "AVG(EXTRACT(EPOCH FROM ad.checkin_time))" in sql
    secure_execute.validate_sql(
        sql,
        tables=set(meta["tables"]),
        columns=catalog_module.bare_columns(),
        aliases=set(meta["aliases"]),
    )


def test_spec_example_compiles():
    from owl.ai import ir2

    ir = ir2.validate(spec_example())
    sql, params, meta = compiler.compile(ir)
    lowered = sql.lower()
    assert lowered.startswith("select") and lowered.count("select") == 1
    assert "join employees e" in lowered and "join departments d" in lowered
    assert "group by" in lowered and "order by" in lowered
    assert "2026-09-01" not in sql and "Active" not in sql  # all values bound
    assert set(params.values()) >= {"2026-09-01", "2026-09-30", "Active"}
    assert "departments" in meta["tables"] and "employees" in meta["tables"]
    assert "average_late_minutes" in meta["aliases"]
    assert meta["outputs"] == ["department", "average_late_minutes"]


def test_expressions_case_having():
    from owl.ai import ir2

    ir = ir2.validate({
        "source": "attendance",
        "select": [
            {"field": "department"},
            {"expression": {"op": "/", "args": [{"field": "minutes_worked"}, {"literal": 60}]}, "alias": "hours"},
            {"case": {"whens": [{"when": {"field": "status", "operator": "=", "value": "x"}, "then": 1}], "else": 0}, "alias": "flag"},
            {"aggregate": "COUNT", "field": "*", "alias": "n"},
        ],
        "filters": {"field": "department", "operator": "=", "value": "AHRD"},
        "group_by": ["department"],
        "having": {"field": "n", "operator": ">", "value": 2},
        "order_by": [{"field": "n", "direction": "DESC"}],
        "limit": 5, "offset": 10, "distinct": True,
    })
    sql, params, meta = compiler.compile(ir)
    assert "DISTINCT" in sql and "HAVING" in sql
    assert "CASE WHEN" in sql and "/" in sql
    assert set(params.values()) >= {"AHRD", 60, 2}
    assert {"hours", "flag", "n"} <= set(meta["outputs"])


def test_explicit_joins():
    from owl.ai import ir2

    ir = ir2.validate({
        "source": "training",
        "select": [{"field": "full_name"}, {"field": "venue"}],
        "joins": [{"table": "venues", "type": "LEFT"}],
        "filters": {"field": "venue", "operator": "=", "value": "Hall"},
        "limit": 5,
    })
    sql, params, meta = compiler.compile(ir)
    assert "venues v" in sql and "INNER" not in sql
    assert sql.lower().count("venues v") == 1  # explicit + auto-join deduped
    assert "venues" in meta["tables"] and "v" in meta["aliases"]
    assert params["p0"] == "Hall"


def test_inner_join_type():
    from owl.ai import ir2

    ir = ir2.validate({
        "source": "leave",
        "select": [{"field": "leave_type"}],
        "joins": [{"table": "leave_types", "type": "INNER"}],
        "group_by": ["leave_type"],
        "limit": 5,
    })
    sql, _, _ = compiler.compile(ir)
    assert "INNER JOIN leave_types" in sql


def test_value_smuggling_stays_bound():
    from owl.ai import ir2

    evil = "'; DROP TABLE employees;--"
    ir = ir2.validate({
        "source": "attendance",
        "select": [{"field": "department"}],
        "filters": {"field": "department", "operator": "=", "value": evil},
        "limit": 5,
    })
    sql, params, _ = compiler.compile(ir)
    assert evil not in sql
    assert evil in set(params.values())
    assert sql.strip().lower().startswith("select")
