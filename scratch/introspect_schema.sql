-- ==========================================
-- DATABASE SCHEMA EXTRACT
-- ==========================================

-- Functions:
-- Table: units
CREATE TABLE IF NOT EXISTS units (
    unit_id INTEGER NOT NULL DEFAULT nextval('units_unit_id_seq'::regclass),
    unit_name VARCHAR(255) NOT NULL,
    CONSTRAINT units_pkey PRIMARY KEY (unit_id)
);

-- Table: ranks
CREATE TABLE IF NOT EXISTS ranks (
    rank_id INTEGER NOT NULL DEFAULT nextval('ranks_rank_id_seq'::regclass),
    rank_name VARCHAR(255) NOT NULL,
    CONSTRAINT ranks_pkey PRIMARY KEY (rank_id)
);

-- Table: employment_types
CREATE TABLE IF NOT EXISTS employment_types (
    emp_type_id INTEGER NOT NULL DEFAULT nextval('employment_types_emp_type_id_seq'::regclass),
    emp_type_name VARCHAR(100) NOT NULL,
    CONSTRAINT employment_types_pkey PRIMARY KEY (emp_type_id)
);

-- Table: employee_statuses
CREATE TABLE IF NOT EXISTS employee_statuses (
    status_id INTEGER NOT NULL DEFAULT nextval('employee_statuses_status_id_seq'::regclass),
    status_name VARCHAR(100) NOT NULL,
    CONSTRAINT employee_statuses_pkey PRIMARY KEY (status_id)
);

-- Table: employees
CREATE TABLE IF NOT EXISTS employees (
    id_no VARCHAR(64) NOT NULL,
    serial_no INTEGER NOT NULL DEFAULT nextval('employees_serial_no_seq'::regclass),
    full_name VARCHAR(255) NOT NULL,
    sex VARCHAR(10) NULL,
    unit_id INTEGER NULL,
    rank_id INTEGER NULL,
    emp_type_id INTEGER NULL,
    status_id INTEGER NULL,
    remark TEXT NULL,
    location_id INTEGER NULL,
    department_id INTEGER NULL,
    gl_id INTEGER NULL,
    CONSTRAINT employees_pkey PRIMARY KEY (id_no)
);

-- Table: employee_location_history
CREATE TABLE IF NOT EXISTS employee_location_history (
    history_id INTEGER NOT NULL DEFAULT nextval('employee_location_history_history_id_seq'::regclass),
    id_no VARCHAR(64) NULL,
    location_id INTEGER NULL,
    start_date DATE NOT NULL,
    end_date DATE NULL,
    CONSTRAINT employee_location_history_pkey PRIMARY KEY (history_id)
);

-- Table: locations
CREATE TABLE IF NOT EXISTS locations (
    location_id INTEGER NOT NULL DEFAULT nextval('locations_location_id_seq'::regclass),
    location_name VARCHAR(100) NOT NULL,
    CONSTRAINT locations_pkey PRIMARY KEY (location_id)
);

-- Table: employee_department_history
CREATE TABLE IF NOT EXISTS employee_department_history (
    history_id INTEGER NOT NULL DEFAULT nextval('employee_department_history_history_id_seq'::regclass),
    id_no VARCHAR(64) NULL,
    department_id INTEGER NULL,
    start_date DATE NOT NULL,
    end_date DATE NULL,
    CONSTRAINT employee_department_history_pkey PRIMARY KEY (history_id)
);

-- Table: departments
CREATE TABLE IF NOT EXISTS departments (
    department_id INTEGER NOT NULL DEFAULT nextval('departments_department_id_seq'::regclass),
    department_name VARCHAR(255) NOT NULL,
    CONSTRAINT departments_pkey PRIMARY KEY (department_id)
);

-- Table: employee_gl_history
CREATE TABLE IF NOT EXISTS employee_gl_history (
    history_id INTEGER NOT NULL DEFAULT nextval('employee_gl_history_history_id_seq'::regclass),
    id_no VARCHAR(64) NULL,
    gl_id INTEGER NULL,
    start_date DATE NOT NULL,
    end_date DATE NULL,
    CONSTRAINT employee_gl_history_pkey PRIMARY KEY (history_id)
);

-- Table: grade_levels
CREATE TABLE IF NOT EXISTS grade_levels (
    gl_id INTEGER NOT NULL DEFAULT nextval('grade_levels_gl_id_seq'::regclass),
    gl_name VARCHAR(50) NOT NULL,
    CONSTRAINT grade_levels_pkey PRIMARY KEY (gl_id)
);

-- Table: employee_trainings
CREATE TABLE IF NOT EXISTS employee_trainings (
    training_id INTEGER NOT NULL DEFAULT nextval('employee_trainings_training_id_seq'::regclass),
    id_no VARCHAR(64) NULL,
    venue_id INTEGER NULL,
    consultant_id INTEGER NULL,
    location_id INTEGER NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    CONSTRAINT employee_trainings_pkey PRIMARY KEY (training_id)
);

-- Table: venues
CREATE TABLE IF NOT EXISTS venues (
    venue_id INTEGER NOT NULL DEFAULT nextval('venues_venue_id_seq'::regclass),
    venue_name VARCHAR(255) NOT NULL,
    CONSTRAINT venues_pkey PRIMARY KEY (venue_id)
);

-- Table: consultants
CREATE TABLE IF NOT EXISTS consultants (
    consultant_id INTEGER NOT NULL DEFAULT nextval('consultants_consultant_id_seq'::regclass),
    consultant_name VARCHAR(255) NOT NULL,
    CONSTRAINT consultants_pkey PRIMARY KEY (consultant_id)
);

-- Table: quarantine_card_swipes
CREATE TABLE IF NOT EXISTS quarantine_card_swipes (
    id INTEGER NOT NULL DEFAULT nextval('quarantine_card_swipes_id_seq'::regclass),
    id_no VARCHAR(64) NULL,
    location_name VARCHAR(128) NULL,
    swipe_time TIMESTAMP WITH TIME ZONE NOT NULL,
    quarantined_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    employee_name VARCHAR(255) NULL,
    CONSTRAINT quarantine_card_swipes_pkey PRIMARY KEY (id)
);

-- Table: quarantine_trainings
CREATE TABLE IF NOT EXISTS quarantine_trainings (
    id INTEGER NOT NULL DEFAULT nextval('quarantine_trainings_id_seq'::regclass),
    id_no VARCHAR(64) NOT NULL,
    venue_name VARCHAR(255) NULL,
    consultant_name VARCHAR(255) NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    quarantined_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT quarantine_trainings_pkey PRIMARY KEY (id)
);

-- Table: employee_unit_history
CREATE TABLE IF NOT EXISTS employee_unit_history (
    history_id INTEGER NOT NULL DEFAULT nextval('employee_unit_history_history_id_seq'::regclass),
    id_no VARCHAR(64) NULL,
    unit_id INTEGER NULL,
    start_date DATE NOT NULL,
    end_date DATE NULL,
    CONSTRAINT employee_unit_history_pkey PRIMARY KEY (history_id)
);

-- Table: employee_rank_history
CREATE TABLE IF NOT EXISTS employee_rank_history (
    history_id INTEGER NOT NULL DEFAULT nextval('employee_rank_history_history_id_seq'::regclass),
    id_no VARCHAR(64) NULL,
    rank_id INTEGER NULL,
    start_date DATE NOT NULL,
    end_date DATE NULL,
    CONSTRAINT employee_rank_history_pkey PRIMARY KEY (history_id)
);

-- Table: employee_leaves
CREATE TABLE IF NOT EXISTS employee_leaves (
    leave_id INTEGER NOT NULL DEFAULT nextval('employee_leaves_leave_id_seq'::regclass),
    id_no VARCHAR(64) NULL,
    leave_type_id INTEGER NULL,
    start_date DATE NOT NULL,
    end_date DATE NULL,
    CONSTRAINT employee_leaves_pkey PRIMARY KEY (leave_id)
);

-- Table: leave_types
CREATE TABLE IF NOT EXISTS leave_types (
    leave_type_id INTEGER NOT NULL DEFAULT nextval('leave_types_leave_type_id_seq'::regclass),
    leave_type_name VARCHAR(100) NOT NULL,
    CONSTRAINT leave_types_pkey PRIMARY KEY (leave_type_id)
);

-- Table: file_ingestion_meta
CREATE TABLE IF NOT EXISTS file_ingestion_meta (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    original_filename TEXT NOT NULL,
    normalized_filename TEXT NOT NULL,
    department TEXT NULL,
    report_type TEXT NULL,
    period DATE NULL,
    version INTEGER NULL,
    file_path TEXT NOT NULL,
    checksum_sha256 TEXT NOT NULL,
    file_size_bytes BIGINT NULL,
    status TEXT NULL DEFAULT 'pending'::text,
    error_context JSONB NULL,
    detected_at TIMESTAMP WITH TIME ZONE NULL DEFAULT now(),
    processed_at TIMESTAMP WITH TIME ZONE NULL,
    created_at TIMESTAMP WITH TIME ZONE NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NULL DEFAULT now(),
    CONSTRAINT file_ingestion_meta_pkey PRIMARY KEY (id)
);

-- Table: employee_card_swipes
CREATE TABLE IF NOT EXISTS employee_card_swipes (
    swipe_id INTEGER NOT NULL DEFAULT nextval('employee_card_swipes_swipe_id_seq'::regclass),
    id_no VARCHAR(64) NULL,
    location_id INTEGER NULL,
    swipe_time TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT employee_card_swipes_pkey PRIMARY KEY (swipe_id)
);

-- Foreign Keys:
ALTER TABLE employees ADD CONSTRAINT employees_department_id_fkey FOREIGN KEY (department_id) REFERENCES departments (department_id);
ALTER TABLE employees ADD CONSTRAINT employees_emp_type_id_fkey FOREIGN KEY (emp_type_id) REFERENCES employment_types (emp_type_id);
ALTER TABLE employees ADD CONSTRAINT employees_gl_id_fkey FOREIGN KEY (gl_id) REFERENCES grade_levels (gl_id);
ALTER TABLE employees ADD CONSTRAINT employees_rank_id_fkey FOREIGN KEY (rank_id) REFERENCES ranks (rank_id);
ALTER TABLE employees ADD CONSTRAINT employees_status_id_fkey FOREIGN KEY (status_id) REFERENCES employee_statuses (status_id);
ALTER TABLE employees ADD CONSTRAINT employees_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES units (unit_id);
ALTER TABLE employees ADD CONSTRAINT fk_employees_location FOREIGN KEY (location_id) REFERENCES locations (location_id);
ALTER TABLE employee_location_history ADD CONSTRAINT employee_location_history_id_no_fkey FOREIGN KEY (id_no) REFERENCES employees (id_no);
ALTER TABLE employee_location_history ADD CONSTRAINT employee_location_history_location_id_fkey FOREIGN KEY (location_id) REFERENCES locations (location_id);
ALTER TABLE employee_department_history ADD CONSTRAINT employee_department_history_department_id_fkey FOREIGN KEY (department_id) REFERENCES departments (department_id);
ALTER TABLE employee_department_history ADD CONSTRAINT employee_department_history_id_no_fkey FOREIGN KEY (id_no) REFERENCES employees (id_no);
ALTER TABLE employee_gl_history ADD CONSTRAINT employee_gl_history_gl_id_fkey FOREIGN KEY (gl_id) REFERENCES grade_levels (gl_id);
ALTER TABLE employee_gl_history ADD CONSTRAINT employee_gl_history_id_no_fkey FOREIGN KEY (id_no) REFERENCES employees (id_no);
ALTER TABLE employee_trainings ADD CONSTRAINT employee_trainings_consultant_id_fkey FOREIGN KEY (consultant_id) REFERENCES consultants (consultant_id);
ALTER TABLE employee_trainings ADD CONSTRAINT employee_trainings_id_no_fkey FOREIGN KEY (id_no) REFERENCES employees (id_no);
ALTER TABLE employee_trainings ADD CONSTRAINT employee_trainings_location_id_fkey FOREIGN KEY (location_id) REFERENCES locations (location_id);
ALTER TABLE employee_trainings ADD CONSTRAINT employee_trainings_venue_id_fkey FOREIGN KEY (venue_id) REFERENCES venues (venue_id);
ALTER TABLE employee_unit_history ADD CONSTRAINT employee_unit_history_id_no_fkey FOREIGN KEY (id_no) REFERENCES employees (id_no);
ALTER TABLE employee_unit_history ADD CONSTRAINT employee_unit_history_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES units (unit_id);
ALTER TABLE employee_rank_history ADD CONSTRAINT employee_rank_history_id_no_fkey FOREIGN KEY (id_no) REFERENCES employees (id_no);
ALTER TABLE employee_rank_history ADD CONSTRAINT employee_rank_history_rank_id_fkey FOREIGN KEY (rank_id) REFERENCES ranks (rank_id);
ALTER TABLE employee_leaves ADD CONSTRAINT employee_leaves_id_no_fkey FOREIGN KEY (id_no) REFERENCES employees (id_no);
ALTER TABLE employee_leaves ADD CONSTRAINT employee_leaves_leave_type_id_fkey FOREIGN KEY (leave_type_id) REFERENCES leave_types (leave_type_id);
ALTER TABLE employee_card_swipes ADD CONSTRAINT employee_card_swipes_id_no_fkey FOREIGN KEY (id_no) REFERENCES employees (id_no);
ALTER TABLE employee_card_swipes ADD CONSTRAINT employee_card_swipes_location_id_fkey FOREIGN KEY (location_id) REFERENCES locations (location_id);


-- Triggers:
CREATE TRIGGER trg_log_employee_history AFTER INSERT OR UPDATE ON public.employees FOR EACH ROW EXECUTE FUNCTION log_combined_history();
