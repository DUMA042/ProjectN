"""Policy tests: open-allow outcomes with sensitive-access audit trails."""
from __future__ import annotations

import logging

from owl.ai import policy


def test_sensitive_fields_listed_for_audit(caplog):
    ir = {
        "source": "attendance",
        "select": [{"field": "full_name"}, {"field": "checkin_time"}],
        "filters": {"field": "phone_number", "operator": "IS NOT NULL"},
    }
    with caplog.at_level(logging.INFO, logger="owl.ai.policy"):
        out = policy.evaluate(ir)
    assert out == {"allowed": True, "sensitive": ["full_name", "phone_number"]}
    assert "full_name" in caplog.text and "phone_number" in caplog.text


def test_public_query_lists_nothing_sensitive(caplog):
    ir = {
        "source": "attendance",
        "select": [{"field": "department"}],
        "filters": {"field": "work_date", "operator": ">=", "value": "2026-09-01"},
    }
    with caplog.at_level(logging.INFO, logger="owl.ai.policy"):
        out = policy.evaluate(ir)
    assert out == {"allowed": True, "sensitive": []}
