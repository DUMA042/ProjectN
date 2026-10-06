"""Catalog tests: tiers, consistency, and model-view purity (no row data)."""
from __future__ import annotations

import json

from owl.ai import catalog


def test_sensitive_tiers():
    f = catalog.ENTITIES["attendance"]["fields"]
    for sensitive in ("full_name", "id_no", "phone_number", "sex", "employment_status"):
        assert f[sensitive]["visibility"] == "sensitive"
        assert f[sensitive]["authorization"] == "controlled"
    for public in ("department", "work_date", "checkin_time", "minutes_worked", "status"):
        assert f[public]["visibility"] == "public"


def test_join_maps_consistent():
    for (entity, key) in catalog.JOINS:
        assert entity in catalog.ENTITIES
        assert key in catalog.JOIN_TABLES
    for field, key in catalog.FIELD_JOINS.items():
        assert key in catalog.JOIN_TABLES
    assert catalog.join_key_for("attendance", "departments") == "department"
    assert catalog.join_key_for("attendance", "attendance_daily") is None
    assert catalog.bare_columns() >= {"full_name", "id_no", "work_date", "department_name"}


def test_model_view_has_no_row_data():
    view = catalog.for_model()
    blob = json.dumps(view)
    assert "employees" in blob  # entity names are vocabulary, not records
    assert set(view.keys()) == {"version", "entities"}
    for ent in view["entities"].values():
        assert set(ent.keys()) == {"description", "fields", "joins"}
        for spec in ent["fields"].values():
            assert set(spec.keys()) == {"description", "type", "operators", "aggregatable", "visibility"}
