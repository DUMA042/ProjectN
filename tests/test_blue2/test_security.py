"""Security matrix: prohibited operations, smuggling, caps, boundary scans."""
from __future__ import annotations

import pytest

from owl.ai.secure_execute import SecurityError, validate_sql

ALLOW = {
    "tables": {"employees", "attendance_daily", "departments"},
    "columns": {"full_name", "id_no", "department_name", "department_id", "status", "work_date"},
    "aliases": {"e", "ad", "d", "n"},
}

GOOD = (
    'SELECT e.full_name, COUNT(*) AS "n" FROM employees e '
    "LEFT JOIN departments d ON d.department_id = e.department_id "
    "WHERE e.full_name = :p0 GROUP BY e.full_name ORDER BY \"n\" DESC LIMIT :p1"
)


def test_legit_sql_passes():
    validate_sql(GOOD, **ALLOW)


def test_prohibited_statements_rejected():
    hostile = [
        "INSERT INTO employees VALUES (1)",
        "UPDATE employees SET full_name = 'x'",
        "DELETE FROM employees",
        "MERGE INTO t USING s ON true WHEN MATCHED THEN UPDATE",
        "TRUNCATE employees",
        "DROP TABLE employees",
        "ALTER TABLE employees ADD COLUMN x INT",
        "CREATE TABLE evil (x INT)",
        "GRANT SELECT ON t TO r",
        "VACUUM employees",
        "EXPLAIN SELECT 1",
        "COPY employees TO '/tmp/x'",
        "CALL something()",
        "SELECT 1; SELECT 2",
        "SELECT * FROM employees; DROP TABLE x",
        "SELECT pg_sleep(10)",
        "SELECT current_setting('x')",
        "SELECT * FROM pg_shadow",
        "SELECT * FROM information_schema.tables",
        "SELECT * FROM users",
        "SELECT password FROM employees",
        "SELECT * FROM employees WHERE x = 1 UNION SELECT password",
        "WITH cte AS (SELECT 1) SELECT * FROM cte",
    ]
    for sql in hostile:
        with pytest.raises(SecurityError):
            validate_sql(sql, **ALLOW)


def test_smuggled_values_are_inert_literals():
    # Attack text inside a properly-quoted literal cannot create statements:
    # the stripper consumes it as one string, so no second statement exists.
    validate_sql(GOOD, **ALLOW)
    sneaky = "SELECT e.full_name FROM employees e WHERE e.full_name = 'x''; DROP TABLE employees;--'"
    validate_sql(sneaky, **ALLOW)  # must NOT raise: nothing executable outside quotes
    # The same attack UNQUOTED is a second statement and must fail.
    bare = "SELECT e.full_name FROM employees e WHERE e.full_name = 'x'; DROP TABLE employees"
    with pytest.raises(SecurityError):
        validate_sql(bare, **ALLOW)


def test_complexity_caps():
    many_joins = "SELECT e.full_name FROM employees e " + " ".join(
        f"LEFT JOIN departments d{i} ON d{i}.department_id = e.department_id" for i in range(5)
    )
    with pytest.raises(SecurityError):
        validate_sql(many_joins, **ALLOW)


def test_model_boundary_has_no_db_access():
    """Planner/narration/compiler modules must not touch credentials, sessions, or vaults."""
    from pathlib import Path

    ai_dir = Path(__file__).resolve().parent.parent.parent / "owl" / "ai"
    for name in ("pipeline.py", "narrate.py", "compiler.py", "ir2.py", "policy.py", "catalog.py"):
        src = (ai_dir / name).read_text(encoding="utf-8")
        for token in ("get_session", "create_engine", "password", "secret",
                      "vault", "DATABASE_URL", "psycopg2"):
            assert token not in src, f"{name} references forbidden '{token}'"
