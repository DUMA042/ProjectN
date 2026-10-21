"""Log redaction + production level policy (pure, no I/O)."""
from __future__ import annotations

import logging

from owl.config import Settings
from owl.logger import REDACTED, RedactionFilter, redact_pii


def test_redacts_names_and_ids():
    line = "Row 1: INSERT id_no=2029 name='ADEDEJI ADEWALE MORUF'"
    out = redact_pii(line)
    assert "ADEDEJI" not in out
    assert "2029" not in out
    assert f"id_no={REDACTED}" in out


def test_redacts_double_quoted_and_staff_id_variants():
    assert "Alice" not in redact_pii('full_name="Alice Ama"')
    assert "E001" not in redact_pii("staff_id=E001")
    assert "1234" not in redact_pii("employee_id: 1234")


def test_redacts_api_key_shapes():
    out = redact_pii("using key sk-abcdef1234567890")
    assert "sk-abcdef1234567890" not in out


def test_leaves_non_pii_text_alone():
    line = "attendance_daily rebuilt: 500 rows (2026-08-01..2026-08-31)"
    assert redact_pii(line) == line


def _record(level: int, message: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="owl.test", level=level, pathname=__file__, lineno=1,
        msg=message, args=(), exc_info=None,
    )


def test_filter_redacts_info_and_above():
    record = _record(logging.INFO, "id_no=2029 name='Alice Ama'")
    RedactionFilter().filter(record)
    assert "2029" not in record.getMessage()
    assert "Alice" not in record.getMessage()


def test_filter_leaves_debug_verbatim():
    record = _record(logging.DEBUG, "id_no=2029 name='Alice Ama'")
    RedactionFilter().filter(record)
    assert "2029" in record.getMessage()
    assert "Alice" in record.getMessage()


def test_production_defaults_to_warning():
    prod = Settings(environment="production", log_level="INFO")
    assert prod.effective_log_level == "WARNING"
    assert prod.docs_enabled is False
    # An explicit non-INFO choice is honoured.
    assert Settings(environment="production", log_level="ERROR").effective_log_level == "ERROR"


def test_development_keeps_level_and_docs():
    dev = Settings(environment="development", log_level="INFO")
    assert dev.effective_log_level == "INFO"
    assert dev.is_development is True
    assert dev.docs_enabled is True
