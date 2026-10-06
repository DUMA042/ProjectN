"""Deterministic individual-report cells + summaries (pure, no I/O)."""
from __future__ import annotations

from datetime import date, datetime

from owl.reports.individual import (
    ReportContext,
    build_employee_report,
    file_stem,
    period_label,
    report_dates,
    resolve_roster,
)
from owl.reports.individual_docx import month_chunks

WH = {
    "monday": {"checkin": {"late_after": "08:00"}, "checkout": {"early_before": "17:00"}},
    "tuesday": {"checkin": {"late_after": "08:00"}, "checkout": {"early_before": "17:00"}},
    "wednesday": {"checkin": {"late_after": "08:00"}, "checkout": {"early_before": "17:00"}},
    "thursday": {"checkin": {"late_after": "08:00"}, "checkout": {"early_before": "17:00"}},
    "friday": {"checkin": {"late_after": "08:00"}, "checkout": {"early_before": "17:00"}},
}
DOWS = [0, 1, 2, 3, 4]

EMP = {"id_no": "E1", "full_name": "Alice", "sex": "F", "department": "HR",
       "grade_level": "5", "rank": "R", "employment_status": "Active", "location": "HQ"}


def make_ctx(holidays=frozenset()):
    return ReportContext(WH, set(holidays), ["Active"], 1, DOWS, True, date(2026, 8, 31))


def dt(hm):
    return datetime(2026, 8, 3, int(hm[:2]), int(hm[3:5]))


def test_present_late_leave_holiday_absent_codes():
    # Mon 3 present normal, Tue 4 late, Wed 5 leave, Tue 25 holiday, Thu 6 absent.
    days = [date(2026, 8, d) for d in (3, 4, 5, 6, 25)]
    data = {
        "swipes": {date(2026, 8, 3): (dt("07:50"), dt("17:10")),
                   date(2026, 8, 4): (dt("09:05"), dt("17:10"))},
        "leaves": [(date(2026, 8, 5), date(2026, 8, 5))],
        "trainings": [],
    }
    rep = build_employee_report(EMP, data, days, make_ctx(holidays={date(2026, 8, 25)}))
    by_date = {c["date"]: c for c in rep["days"]}
    assert (by_date[date(2026, 8, 3)]["ci"], by_date[date(2026, 8, 3)]["co"]) == ("07:50", "17:10")
    assert by_date[date(2026, 8, 4)]["ci"] == "09:05"
    assert (by_date[date(2026, 8, 5)]["ci"], by_date[date(2026, 8, 5)]["co"]) == ("L", "L")
    assert (by_date[date(2026, 8, 25)]["ci"], by_date[date(2026, 8, 25)]["co"]) == ("H", "H")
    assert (by_date[date(2026, 8, 6)]["ci"], by_date[date(2026, 8, 6)]["co"]) == ("", "")
    s = rep["summary"]
    assert s["days_present"] == 2 and s["days_absent"] == 1 and s["days_on_leave"] == 1
    assert s["days_late"] == 1 and s["total_minutes_late"] == 65
    assert s["expected_workdays"] == 4  # holiday excluded


def test_incomplete_single_swipe():
    days = [date(2026, 8, 3)]
    data = {"swipes": {date(2026, 8, 3): (dt("08:00"), dt("08:00"))},
            "leaves": [], "trainings": []}
    rep = build_employee_report(EMP, data, days, make_ctx())
    assert (rep["days"][0]["ci"], rep["days"][0]["co"]) == ("08:00", "IN")
    assert rep["summary"]["incomplete_swipe_days"] == 1


def test_training_code_and_weekend_blank():
    # Sat 8 = weekend (blank), Mon 10 training.
    days = [date(2026, 8, 8), date(2026, 8, 10)]
    data = {"swipes": {}, "leaves": [],
            "trainings": [(date(2026, 8, 10), date(2026, 8, 10))]}
    rep = build_employee_report(EMP, data, days, make_ctx())
    assert (rep["days"][0]["ci"], rep["days"][0]["co"]) == ("", "")
    assert (rep["days"][1]["ci"], rep["days"][1]["co"]) == ("T", "T")
    assert rep["summary"]["days_in_training"] == 1


def test_month_chunks_and_labels():
    assert period_label(date(2026, 8, 1), date(2026, 8, 31)) == "August 2026"
    assert "to" in period_label(date(2026, 8, 30), date(2026, 9, 2))
    chunks = month_chunks([date(2026, 8, 31), date(2026, 9, 1), date(2026, 9, 2)])
    assert [len(c) for c in chunks] == [1, 2]
    stem = file_stem("HQ", date(2026, 8, 1), date(2026, 8, 31))
    assert stem.startswith("Individual_Attendance_Details_August_2026_HQ")


def test_roster_id_cap():
    import pytest

    with pytest.raises(ValueError, match="Too many individuals"):
        resolve_roster(None, "", [], ["x"] * 2001)


ROSTER_DDL = """
CREATE TABLE departments (department_id INTEGER PRIMARY KEY, department_name TEXT);
CREATE TABLE grade_levels (gl_id INTEGER PRIMARY KEY, gl_name TEXT);
CREATE TABLE ranks (rank_id INTEGER PRIMARY KEY, rank_name TEXT);
CREATE TABLE employee_statuses (status_id INTEGER PRIMARY KEY, status_name TEXT);
CREATE TABLE locations (location_id INTEGER PRIMARY KEY, location_name TEXT);
CREATE TABLE employees (
    id_no TEXT PRIMARY KEY, full_name TEXT, sex TEXT,
    department_id INTEGER, gl_id INTEGER, rank_id INTEGER,
    status_id INTEGER, location_id INTEGER);
"""


def _roster_session():
    from sqlalchemy import create_engine, text as _text
    from sqlalchemy.orm import Session as _Session

    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        for stmt in ROSTER_DDL.strip().split(";"):
            if stmt.strip():
                conn.execute(_text(stmt))
        conn.execute(_text("INSERT INTO departments VALUES (1,'HR'),(2,'IT')"))
        conn.execute(_text("INSERT INTO locations VALUES (1,'HQ'),(2,'Branch')"))
        conn.execute(_text("INSERT INTO employee_statuses VALUES (1,'Active')"))
        conn.execute(_text(
            "INSERT INTO employees VALUES "
            "('E1','Alice Ama','F',1,NULL,NULL,1,1),"
            "('E2','Bob Boateng','M',2,NULL,NULL,1,1),"
            "('E3','Ama Serwaa','F',2,NULL,NULL,1,2)"))
        conn.commit()
    return _Session(engine)


def test_resolve_roster_search_scopes_all():
    with _roster_session() as s:
        assert {e["id_no"] for e in resolve_roster(s, "", [], [], "")} == {"E1", "E2", "E3"}
        # Search narrows: "ama" matches Alice Ama + Ama Serwaa (name or ID).
        assert {e["id_no"] for e in resolve_roster(s, "", [], [], "ama")} == {"E1", "E3"}
        assert [e["id_no"] for e in resolve_roster(s, "", [], [], "E2")] == ["E2"]
        # Explicit IDs bypass department/location/search scope.
        only = resolve_roster(s, "Branch", ["IT"], ["E1"], "zzz")
        assert [e["id_no"] for e in only] == ["E1"]
        # Location + department narrowing still applies without IDs.
        assert [e["id_no"] for e in resolve_roster(s, "HQ", ["IT"], [], "")] == ["E2"]


def test_report_dates_follow_rules():
    mon_fri = {1, 2, 3, 4, 5}  # ISO weekdays, matching get_working_weekdays()
    # Sun 2 – Fri 7 Aug 2026: weekend dropped, weekday holiday kept.
    out = report_dates(date(2026, 8, 2), date(2026, 8, 7), mon_fri, {date(2026, 8, 25)})
    assert [d.isoweekday() for d in out] == [1, 2, 3, 4, 5]
    # Sunday holiday still renders as a single H column (union rule).
    out = report_dates(date(2026, 8, 2), date(2026, 8, 2), mon_fri, {date(2026, 8, 2)})
    assert out == [date(2026, 8, 2)]
    # Pure weekend range with no holidays: empty (route turns this into a 400).
    assert report_dates(date(2026, 8, 8), date(2026, 8, 9), mon_fri, set()) == []
    # Saturday configured as working: included.
    out = report_dates(date(2026, 8, 8), date(2026, 8, 8), {1, 2, 3, 4, 5, 6}, set())
    assert out == [date(2026, 8, 8)]


def test_docx_grids_have_no_weekend_columns(tmp_path):
    from owl.reports.individual_docx import build_individual_docx

    days = report_dates(date(2026, 8, 1), date(2026, 8, 9), {1, 2, 3, 4, 5}, set())
    assert [d.isoweekday() for d in days] == [1, 2, 3, 4, 5]
    data = {"swipes": {}, "leaves": [], "trainings": []}
    rep = build_employee_report(EMP, data, days, make_ctx())
    out = tmp_path / "week.docx"
    build_individual_docx("HQ", "August 2026", "meta", [("HR", [rep])], days, out)
    from docx import Document as _Doc

    doc = _Doc(str(out))
    labels = [c.text for t in doc.tables for c in t.rows[0].cells]
    assert not any(v.startswith(("Sat", "Sun")) for v in labels)
    assert any(v.startswith("Mon") for v in labels)
