"""Rule-value SQL guards: broken values fail loudly, never reach SQL (pure)."""
from __future__ import annotations

import pytest

import owl.rules.query_builder as qb


@pytest.fixture()
def rules(monkeypatch):
    data = {
        "working_hours": {
            "monday": {
                "checkin": {"early_before": "07:30", "normal_start": "07:30",
                            "normal_end": "09:00", "late_after": "09:00"},
                "checkout": {"early_before": "17:00", "normal_start": "17:00",
                             "normal_end": "18:00", "late_after": "18:00"},
            }
        },
        "holidays": {"dates": ["2026-08-25"]},
        "eligible_statuses": {"statuses": ["Active"]},
        "incomplete_threshold": {"hours": 1},
    }
    monkeypatch.setattr(qb, "get_rule", lambda k, d=None: data.get(k, d or {}))
    return data


def test_valid_rules_emit_expected_sql(rules):
    sql = qb.build_checkin_classification()
    assert "TIME '09:00'" in sql and "Late Arrival" in sql
    assert "NOT IN ('2026-08-25')" in qb.build_holidays_filter()
    assert "IN ('active')" in qb.build_status_filter()


def test_quote_injection_rejected(rules, monkeypatch):
    monkeypatch.setattr(
        qb, "get_rule",
        lambda k, d=None: {"statuses": ["Active' OR '1'='1"]} if k == "eligible_statuses"
        else rules.get(k, d or {}),
    )
    with pytest.raises(ValueError, match="quotes are not allowed"):
        qb.build_status_filter()
    with pytest.raises(ValueError, match="quotes are not allowed"):
        qb.build_eligible_statuses_filter()


def test_bad_time_rejected(rules, monkeypatch):
    bad = {"monday": {"checkin": {"late_after": "09:00' OR 1=1 --"}}}
    monkeypatch.setattr(qb, "get_rule",
                        lambda k, d=None: bad if k == "working_hours" else rules.get(k, d or {}))
    with pytest.raises(ValueError, match="Invalid time"):
        qb.build_checkin_classification()


def test_bad_holiday_date_rejected(rules, monkeypatch):
    monkeypatch.setattr(
        qb, "get_rule",
        lambda k, d=None: {"dates": ["25/08/2026"]} if k == "holidays" else rules.get(k, d or {}),
    )
    with pytest.raises(ValueError, match="Invalid date"):
        qb.build_holidays_filter()


def test_bad_identifier_rejected():
    with pytest.raises(ValueError, match="Invalid identifier"):
        qb.build_checkin_classification(column="x; DROP TABLE y")
    with pytest.raises(ValueError, match="Invalid identifier"):
        qb.build_holidays_filter(date_col="swipe_date) OR (1=1")
