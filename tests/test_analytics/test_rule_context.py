"""Rule-context audit: garbage rules produce loud warnings, not silent misclassification (pure)."""
from __future__ import annotations

from owl.analytics.classification import validate_rule_context

GOOD = {
    "working_hours": {
        "monday": {
            "checkin": {"late_after": "09:00"},
            "checkout": {"early_before": "17:00"},
        }
    },
    "incomplete_hours": 1,
    "holidays_raw": ["2026-08-25"],
}


def test_clean_context_no_warnings():
    assert validate_rule_context(dict(GOOD)) == []


def test_bad_time_flagged():
    ctx = {"working_hours": {"monday": {"checkin": {"late_after": "nine"}}},
           "incomplete_hours": 1, "holidays_raw": []}
    warnings = validate_rule_context(ctx)
    assert any("late_after" in w for w in warnings)


def test_bad_holiday_and_threshold_flagged():
    ctx = {"working_hours": {}, "incomplete_hours": 0, "holidays_raw": ["25/08/2026"]}
    warnings = validate_rule_context(ctx)
    assert any("not a valid date" in w for w in warnings)
    assert any("positive" in w for w in warnings)
