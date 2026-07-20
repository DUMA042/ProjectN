"""
tests/test_classification.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for the structural classifier and ingest manager logic.
"""

import pytest
import pandas as pd
from datetime import date
from owl.extract.classifier import StructuralClassifier, ReportType, IngestionMetadata


# ── classify() tests (normalised DataFrame column check) ──────────────────────

def test_nominal_classification():
    df = pd.DataFrame(columns=["id_no", "gl", "rank", "employment_type", "name"])
    classifier = StructuralClassifier(df)
    assert classifier.classify() == ReportType.NOMINAL


def test_training_classification():
    df = pd.DataFrame(columns=["id", "venue", "consultant", "start_date"])
    classifier = StructuralClassifier(df)
    assert classifier.classify() == ReportType.TRAINING


def test_card_swipe_classification():
    df = pd.DataFrame(columns=["name", "card_swiping_time", "location"])
    classifier = StructuralClassifier(df)
    assert classifier.classify() == ReportType.CARD_SWIPE


def test_leave_fallback_classification():
    """Leave can be detected via column fingerprint as a fallback."""
    df = pd.DataFrame(columns=["staff_id", "proposed_leave_date", "resumption_date", "leave_type"])
    classifier = StructuralClassifier(df)
    assert classifier.classify() == ReportType.LEAVE


def test_unknown_classification():
    df = pd.DataFrame(columns=["some_random_column", "another_one"])
    classifier = StructuralClassifier(df)
    assert classifier.classify() == ReportType.UNKNOWN


# ── Cross-contamination checks: classify() ────────────────────────────────────
# These ensure more specific fingerprints win when multiple overlap.

def test_card_swipe_with_nominal_columns_wins_card_swipe():
    """
    If a Card Swipe file also has columns that match the Nominal fingerprint,
    it must still be classified as CARD_SWIPE (more specific fingerprint).
    """
    df = pd.DataFrame(columns=[
        "id_no", "gl", "rank",           # matches NOMINAL
        "card_swiping_time",             # matches CARD_SWIPE
        "name", "person_group", "attendance_terminal",
    ])
    classifier = StructuralClassifier(df)
    assert classifier.classify() == ReportType.CARD_SWIPE


def test_training_with_nominal_columns_wins_training():
    """
    If a Training file also has id_no + gl columns, it must still be
    classified as TRAINING (more specific triple fingerprint).
    """
    df = pd.DataFrame(columns=[
        "id_no", "gl",                   # matches NOMINAL
        "venue", "consultant", "start_date",  # matches TRAINING
        "id", "end_date",
    ])
    classifier = StructuralClassifier(df)
    assert classifier.classify() == ReportType.TRAINING


# ── find_best_header_row() tests (raw DataFrame scanning) ─────────────────────

def test_find_best_header_row_card_swipe_with_extra_cols():
    """
    Simulate a Card Swipe file whose header row also contains 'ID No.' and 'GL'.
    This would be a data row that, when normalised, contains id_no and gl values.
    It must still be classified as CARD_SWIPE, not NOMINAL.
    """
    # Row 0 = header with Card Swipe columns PLUS extra Nominal-like columns
    raw = pd.DataFrame([
        ["ID No.", "GL", "ID", "Name", "Person Group", "Card Swiping Time", "Attendance Terminal"],
        ["001", "GL12", "001", "JOHN DOE", "AHRD", "2026-07-20 08:00:00", "Door1"],
    ])
    result = StructuralClassifier.find_best_header_row(raw)
    assert result is not None
    r_type, header_idx = result
    assert r_type == ReportType.CARD_SWIPE, f"Expected CARD_SWIPE, got {r_type}"
    assert header_idx == 0


def test_find_best_header_row_card_swipe_standard():
    """Standard Card Swipe file with exact user-specified columns."""
    raw = pd.DataFrame([
        ["ID", "Name", "Person Group", "Card Swiping Time", "Attendance Terminal"],
        ["001", "JOHN DOE", "AHRD", "2026-07-20 08:00:00", "Door1"],
    ])
    result = StructuralClassifier.find_best_header_row(raw)
    assert result is not None
    r_type, header_idx = result
    assert r_type == ReportType.CARD_SWIPE
    assert header_idx == 0


def test_find_best_header_row_nominal_standard():
    """Standard Nominal Roll file is still classified as NOMINAL."""
    raw = pd.DataFrame([
        ["S/N", "Name", "Sex", "ID No.", "GL", "Rank", "Department", "Location"],
        ["1", "JOHN DOE", "M", "001", "GL12", "Director", "HR", "HQ"],
    ])
    result = StructuralClassifier.find_best_header_row(raw)
    assert result is not None
    r_type, header_idx = result
    assert r_type == ReportType.NOMINAL, f"Expected NOMINAL, got {r_type}"
    assert header_idx == 0


def test_find_best_header_row_training_with_id_no():
    """Training file with an id_no column is still classified as TRAINING."""
    raw = pd.DataFrame([
        ["id_no", "id", "Venue", "Consultant", "Start Date", "End Date"],
        ["001", "TRN01", "Lagos Hall", "ABC Consulting", "2026-01-15", "2026-01-20"],
    ])
    result = StructuralClassifier.find_best_header_row(raw)
    assert result is not None
    r_type, header_idx = result
    assert r_type == ReportType.TRAINING, f"Expected TRAINING, got {r_type}"
    assert header_idx == 0


def test_find_best_header_row_leave_fallback():
    """
    A Leave file that fails positional validation (non-standard layout)
    should still be caught by the column-based LEAVE fingerprint fallback.
    """
    raw = pd.DataFrame([
        ["staff_id", "proposed_leave_date", "resumption_date", "leave_type"],
        ["001", "2026-06-01", "2026-06-15", "Annual"],
    ])
    result = StructuralClassifier.find_best_header_row(raw)
    assert result is not None
    r_type, header_idx = result
    assert r_type == ReportType.LEAVE, f"Expected LEAVE, got {r_type}"


# ── Period extraction & filename generation ───────────────────────────────────

def test_period_extraction():
    today = date.today()
    df = pd.DataFrame({
        "start_date": [pd.Timestamp(today.year, today.month, 15)]
    })
    classifier = StructuralClassifier(df)
    extracted = classifier.extract_period()
    assert extracted.year == today.year
    assert extracted.month == today.month
    assert extracted.day == 1


def test_metadata_filename_generation():
    meta = IngestionMetadata(
        report_type=ReportType.NOMINAL,
        department="AHRD",
        period=date(2024, 2, 1),
        version=1
    )
    assert meta.generate_filename() == "AHRD_Nominal_202402_v1.xlsx"
