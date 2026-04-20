"""
tests/test_classification.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for the structural classifier and ingest manager logic.
"""

import pytest
import pandas as pd
from datetime import date
from owl.extract.classifier import StructuralClassifier, ReportType, IngestionMetadata

def test_nominal_classification():
    # Columns matching Nominal fingerprint
    df = pd.DataFrame(columns=["id_no", "gl", "rank", "employment_type", "name"])
    classifier = StructuralClassifier(df)
    assert classifier.classify() == ReportType.NOMINAL

def test_training_classification():
    # Columns matching Training fingerprint
    df = pd.DataFrame(columns=["id", "venue", "consultant", "start_date"])
    classifier = StructuralClassifier(df)
    assert classifier.classify() == ReportType.TRAINING

def test_card_swipe_classification():
    # Columns matching Card fingerprint
    df = pd.DataFrame(columns=["name", "card_swiping_time", "location"])
    classifier = StructuralClassifier(df)
    assert classifier.classify() == ReportType.CARD_SWIPE

def test_unknown_classification():
    # Random columns
    df = pd.DataFrame(columns=["some_random_column", "another_one"])
    classifier = StructuralClassifier(df)
    assert classifier.classify() == ReportType.UNKNOWN

def test_period_extraction():
    # DataFrame with dates in current month
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
