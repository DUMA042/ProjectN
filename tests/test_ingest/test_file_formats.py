"""The in-app file-format guide must match what the pipeline enforces."""
from __future__ import annotations

from fastapi.testclient import TestClient

from api import main as app_module
from owl.extract.classifier import FINGERPRINTS, ReportType
from owl.ingest.file_specs import FILE_SPECS, USAGE_OPTIONAL, USAGE_IGNORED, USAGE_REQUIRED
from owl.nominal.validator import NOMINAL_SIGNATURE

client = TestClient(app_module.app)

VALID_USAGE = {USAGE_REQUIRED, USAGE_OPTIONAL, USAGE_IGNORED}


def _types() -> dict[str, dict]:
    return {spec["id"]: spec for spec in FILE_SPECS["types"]}


def test_endpoint_returns_all_four_types():
    res = client.get("/api/file-formats")
    assert res.status_code == 200
    body = res.json()
    assert {t["id"] for t in body["types"]} == {
        "nominal",
        "leave",
        "training",
        "card_swipe",
    }
    assert body["filename_pattern"] == "DEPT_TYPE_YYYYMM_vN.xlsx"


def test_every_column_has_a_valid_usage():
    for spec in FILE_SPECS["types"]:
        assert spec["columns"], spec["id"]
        for column in spec["columns"]:
            assert column["usage"] in VALID_USAGE, (spec["id"], column)


def test_nominal_required_positions_cover_the_validator_signature():
    nominal = _types()["nominal"]
    required = {c["index"] for c in nominal["columns"] if c["usage"] == USAGE_REQUIRED}
    assert set(NOMINAL_SIGNATURE) <= required
    # Sex, status and remark are read but are not part of the signature.
    assert {2, 26, 27} <= required
    assert nominal["header_rows"] == 1
    assert nominal["min_columns"] == 29
    assert nominal["positional"] is True


def test_leave_uses_two_header_rows_with_staff_id_at_position_two():
    leave = _types()["leave"]
    assert leave["header_rows"] == 2
    assert leave["data_starts_row"] == 3
    assert leave["positional"] is True
    by_index = {c["index"]: c for c in leave["columns"]}
    assert by_index[2]["header"] == "STAFF ID"
    assert by_index[2]["usage"] == USAGE_REQUIRED
    assert by_index[6]["usage"] == USAGE_REQUIRED
    assert by_index[7]["usage"] == USAGE_REQUIRED


def test_training_and_swipe_cover_their_detection_fingerprints():
    types = _types()
    training = set(types["training"]["required_headers"])
    swipe = set(types["card_swipe"]["required_headers"])
    assert FINGERPRINTS[ReportType.TRAINING] <= training
    assert FINGERPRINTS[ReportType.CARD_SWIPE] <= swipe
    assert "id_no" in training
    assert "name" in swipe
