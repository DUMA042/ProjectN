-- ============================================================================
-- Read-only role for chatbot query execution (run ONCE as the DB owner).
--
--   1. Set a strong password below (never commit it anywhere).
--   2. psql -h localhost -U postgres -d flowdb -f scripts/add_readonly_role.sql
--   3. Set READER_DATABASE_URL in the server .env to the matching string:
--        postgresql+psycopg2://flow_reader:<PASSWORD>@localhost:5432/flowdb
--   4. Restart the API. Without READER_DATABASE_URL the executor falls back
--      to the app session inside a read-only transaction (documented).
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'flow_reader') THEN
        CREATE ROLE flow_reader WITH LOGIN PASSWORD 'CHANGE_ME_STRONG_PASSWORD';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE flowdb TO flow_reader;
GRANT USAGE ON SCHEMA public TO flow_reader;

GRANT SELECT ON public.employees TO flow_reader;
GRANT SELECT ON public.attendance_daily TO flow_reader;
GRANT SELECT ON public.leave_records TO flow_reader;
GRANT SELECT ON public.leave_applications TO flow_reader;
GRANT SELECT ON public.employee_trainings TO flow_reader;
GRANT SELECT ON public.departments TO flow_reader;
GRANT SELECT ON public.grade_levels TO flow_reader;
GRANT SELECT ON public.ranks TO flow_reader;
GRANT SELECT ON public.locations TO flow_reader;
GRANT SELECT ON public.employee_statuses TO flow_reader;
GRANT SELECT ON public.employment_types TO flow_reader;
GRANT SELECT ON public.leave_types TO flow_reader;
GRANT SELECT ON public.venues TO flow_reader;
GRANT SELECT ON public.consultants TO flow_reader;

-- Future tables in public are readable by default under this policy.
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO flow_reader;
