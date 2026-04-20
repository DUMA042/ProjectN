-- owl: PostgreSQL Schema — Single Source of Truth
-- Convention: All DDL is idempotent (CREATE TABLE IF NOT EXISTS).
-- Mirror every table here with a corresponding SQLAlchemy ORM model in models.py.
-- Run via: scripts/init_db.py

-- ── Extensions ────────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- gen_random_uuid() support

-- ── Dimension: Employee ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_employee (
    id             VARCHAR(36)  PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    employee_id    VARCHAR(64)  NOT NULL,
    full_name      VARCHAR(255) NOT NULL,
    department     VARCHAR(128),
    position       VARCHAR(128),
    is_active      BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_employee_employee_id UNIQUE (employee_id)
);

CREATE INDEX IF NOT EXISTS idx_employee_employee_id ON dim_employee (employee_id);

-- ── Dimension: Date ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_date (
    id             VARCHAR(36)  PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    calendar_date  DATE         NOT NULL,
    year           SMALLINT     NOT NULL,
    month          SMALLINT     NOT NULL,
    day            SMALLINT     NOT NULL,
    day_of_week    VARCHAR(16)  NOT NULL,    -- e.g. 'Monday'
    is_weekend     BOOLEAN      NOT NULL,
    week_of_year   SMALLINT     NOT NULL,
    quarter        SMALLINT     NOT NULL,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_date_calendar_date UNIQUE (calendar_date)
);

CREATE INDEX IF NOT EXISTS idx_date_calendar_date ON dim_date (calendar_date);
CREATE INDEX IF NOT EXISTS idx_date_year_month    ON dim_date (year, month);

-- ── Dimension: Leave Type ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_leave_type (
    id               VARCHAR(36)  PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    leave_type_name  VARCHAR(128) NOT NULL,
    description      TEXT,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_leave_type_name UNIQUE (leave_type_name)
);

-- ── Fact: Attendance ──────────────────────────────────────────────────────────
-- Uncomment and extend when the first attendance sheet is ready.
--
-- CREATE TABLE IF NOT EXISTS fact_attendance (
--     id              VARCHAR(36)  PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
--     employee_fk     VARCHAR(36)  NOT NULL REFERENCES dim_employee(id)  ON DELETE RESTRICT,
--     date_fk         VARCHAR(36)  NOT NULL REFERENCES dim_date(id)       ON DELETE RESTRICT,
--     status          VARCHAR(32)  NOT NULL,   -- 'Present' | 'Absent' | 'Leave' | 'Holiday'
--     leave_type_fk   VARCHAR(36)  REFERENCES dim_leave_type(id),
--     notes           TEXT,
--     created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
--     updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
--     CONSTRAINT uq_attendance_employee_date UNIQUE (employee_fk, date_fk)
-- );
--
-- CREATE INDEX IF NOT EXISTS idx_attendance_employee ON fact_attendance (employee_fk);
-- CREATE INDEX IF NOT EXISTS idx_attendance_date     ON fact_attendance (date_fk);
-- CREATE INDEX IF NOT EXISTS idx_attendance_status   ON fact_attendance (status);

-- ── Audit trigger helper ──────────────────────────────────────────────────────
-- Automatically updates `updated_at` on every row change.

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DO $$
DECLARE
    _tbl TEXT;
BEGIN
    FOREACH _tbl IN ARRAY ARRAY['dim_employee', 'dim_date', 'dim_leave_type']
    LOOP
        EXECUTE format(
            'CREATE OR REPLACE TRIGGER trg_%s_updated_at
             BEFORE UPDATE ON %s
             FOR EACH ROW EXECUTE FUNCTION set_updated_at();',
            _tbl, _tbl
        );
    END LOOP;
END;
$$;
