"""Narration-gate tests: provenance rule, templates, fallback (synthetic data only)."""
from __future__ import annotations

import httpx

from owl.ai import narrate


def test_provenance_user_typed_passes_db_only_placeholders():
    rows = [
        {"full_name": "Testperson Alpha", "id_no": "T-001", "checkin_time": "06:58"},
        {"full_name": "Testperson Beta", "id_no": "T-002", "checkin_time": "07:02"},
    ]
    sensitive = {"full_name", "id_no"}
    # User typed T-001 themselves: it may flow; everything else is placeholder'd.
    payload, sub = narrate.prepare("When did T-001 check in?", rows, sensitive)
    assert payload[0]["id_no"] == "T-001"
    assert payload[0]["full_name"] == "[NAME-1]"
    assert payload[1]["full_name"] == "[NAME-2]"
    assert sub["[NAME-1]"] == "Testperson Alpha"
    # Substitution restores exactly.
    assert narrate.substitute("Hi [NAME-1] ([ID-1])", {"[NAME-1]": "A", "[ID-1]": "1"}) == "Hi A (1)"


def test_output_tiers():
    from owl.ai import catalog as catalog_module

    ir = {
        "source": "attendance",
        "select": [
            {"field": "full_name"},
            {"field": "department"},
            {"aggregate": "COUNT", "field": "*", "alias": "n"},
            {"aggregate": "AVG", "field": "minutes_worked", "alias": "avg_min"},
            {"expression": {"op": "COALESCE",
                            "args": [{"field": "full_name"}, {"literal": "?"}]}, "alias": "nm"},
        ],
    }
    tiers = narrate.output_tiers(ir, catalog_module.ENTITIES["attendance"]["fields"])
    assert tiers["full_name"] == "sensitive"
    assert tiers["department"] == "public"
    assert tiers["n"] == "public"  # pure count over anyone
    assert tiers["avg_min"] == "public"  # numeric aggregate
    assert tiers["nm"] == "sensitive"  # expression over a sensitive base


def test_templates_and_fallback():
    rows = [{"full_name": "[NAME-1]", "checkin_time": "06:58"}]
    text = narrate.render("top_early", rows, "August 2026")
    assert text and "[NAME-1]" in text and "06:58" in text
    assert narrate.render("nope", rows, None) is None
    assert "table below" in narrate.fallback_text(3)

    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("slow")

    out = narrate.narrate("q?", [{"a": 1}], transport=httpx.MockTransport(boom))
    assert "table below" in out
