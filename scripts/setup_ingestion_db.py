"""
scripts/setup_ingestion_db.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
One-time setup for the file ingestion metadata tracking table.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from sqlalchemy import text
from owl.load.database import get_session, verify_connection
from owl.logger import get_logger

log = get_logger(__name__)

CREATE_TABLE_SQL = """
-- Ensure pgcrypto for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

DROP TABLE IF EXISTS file_ingestion_meta CASCADE;


CREATE TABLE file_ingestion_meta (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    original_filename TEXT NOT NULL,
    normalized_filename TEXT NOT NULL,
    department TEXT,
    report_type TEXT,
    period DATE GENERATED ALWAYS AS (
        MAKE_DATE(
            CAST(SUBSTRING(SPLIT_PART(normalized_filename, '_', 3) FROM 1 FOR 4) AS INT),
            CAST(SUBSTRING(SPLIT_PART(normalized_filename, '_', 3) FROM 5 FOR 2) AS INT),
            1
        )
    ) STORED,

    version INT,
    file_path TEXT NOT NULL,
    checksum_sha256 TEXT NOT NULL,
    file_size_bytes BIGINT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending','validating','processing','completed','failed','quarantined')),
    error_context JSONB,
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    
    -- Audit columns required by owl.load.models.Base
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE (checksum_sha256, department, report_type, period)
);


-- Indices for performance
CREATE INDEX IF NOT EXISTS idx_ingestion_status ON file_ingestion_meta(status);
CREATE INDEX IF NOT EXISTS idx_ingestion_checksum ON file_ingestion_meta(checksum_sha256);
"""

def setup_ingestion_db() -> None:
    log.info("Starting ingestion database setup...")
    try:
        verify_connection()
        with get_session() as session:
            session.execute(text(CREATE_TABLE_SQL))
            log.info("Metadata table 'file_ingestion_meta' created or already exists.")
    except Exception as exc:
        log.exception(f"Setup failed.")
        if hasattr(exc, "context") and "original_error" in exc.context:
            log.error(f"PostgreSQL ERROR: {exc.context['original_error']}")
        sys.exit(1)



if __name__ == "__main__":
    setup_ingestion_db()
