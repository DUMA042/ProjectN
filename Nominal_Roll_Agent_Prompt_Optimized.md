# Nominal Roll Data Processing — AI Agent Prompt (Optimized)

---

## ⚠️ CRITICAL UPFRONT WARNING — READ BEFORE ANYTHING ELSE

The Nominal Roll file is the **single source of truth for all employee data** in this system. Every other pipeline — Leave, Training, Card Swipes, Kanban — derives its employee references from data that originated here. `employees.id_no` is the primary key that cascades across **11 other tables** as a foreign key. `employees.location_id`, `employees.department_id`, `employees.gl_id`, `employees.rank_id`, `employees.status_id`, `employees.unit_id`, and `employees.emp_type_id` are all foreign keys referencing lookup tables that are also used by history-tracking tables, ingestion tables, and application tables.

**Any mistake here — a wrong data type, a dropped column, a premature schema change without updating downstream tables and code — will corrupt the integrity of the entire database and break every other pipeline.**

This task must be approached with extreme caution. No assumption is acceptable. No change is made without a documented, reviewed plan. The word "assume" should not appear in your plan or code.

---

## ROLE & CONTEXT

Act as a **Senior Software Engineer with deep expertise in Python, PostgreSQL, and data pipeline architecture**. Your task is to build a robust, production-grade pipeline that reads employee records from the Nominal Roll Excel file and upserts them accurately into the database — with full referential integrity, complete history tracking, and zero tolerance for silent data loss.

---

## PRE-CONDITIONS (Mandatory — do ALL of these before writing a single line of plan or code)

### Step 1 — Read and Map the Entire Database Schema

Query and read every table in the database. For each table, record:
- All column names and their **exact data types** (including precision, nullability, and defaults).
- All primary key constraints.
- All foreign key constraints — both the source column and the target table/column.
- All unique constraints.
- All indexes.

Do not summarise or paraphrase the schema. Reproduce it in your plan so the dependency map can be verified before any changes are made.

### Step 2 — Build a Complete Foreign Key Dependency Map

Before touching any table, trace every foreign key that references the tables the Nominal Roll populates. The minimum dependency map you must produce covers these tables and all tables that reference them:

**`employees` table** — referenced (via `id_no`) by:
- `employee_card_swipes`
- `employee_department_history`
- `employee_gl_history`
- `employee_location_history`
- `employee_rank_history`
- `employee_trainings`
- `employee_unit_history`
- `kanban_task_assignees`
- `leave_applications`
- `leave_records`

**Lookup tables populated by Nominal Roll data** — each must be fully traced:
- `departments` → referenced by `employees`, `employee_department_history`, `kanban_boards`
- `grade_levels` → referenced by `employees`, `employee_gl_history`
- `locations` → referenced by `employees`, `employee_location_history`, `employee_card_swipes`, `employee_trainings`
- `ranks` → referenced by `employees`, `employee_rank_history`
- `units` → referenced by `employees`, `employee_unit_history`
- `employment_types` → referenced by `employees`
- `employee_statuses` → referenced by `employees`

For every one of these, state the ON UPDATE and ON DELETE behaviour of each FK constraint. This is critical for understanding whether a schema change will cascade, restrict, or set null.

### Step 3 — Read and Audit the Entire Codebase

Read every file in the codebase. For each file, identify:
- Whether it reads from or writes to any of the tables listed in Step 2.
- Whether it references `employees.serial_no` anywhere — by column name in a query, in an ORM model, in a response serializer, in a type hint, or in a test.
- Whether it references `employees.id_no` and what assumptions it makes about the data type (is it treated as an integer anywhere?).
- Whether it contains the file classification logic, the file validator, the duplicate-detection logic, the folder-routing logic, or the file-naming logic for the Nominal Roll.
- Whether it contains any triggers, stored procedures, or database functions that fire on INSERT or UPDATE to any of the tables in Step 2. List every one of these and what they do.

Do not skip any file. Do not summarise sections — reproduce the relevant code snippets in your audit so they can be reviewed.

### Step 4 — Understand the Current Nominal Roll Pipeline (if one exists)

If a Nominal Roll pipeline already exists in the codebase, trace it completely from inbox to database. If it does not exist, state that explicitly and proceed to plan the new one from scratch. Either way, by the end of Step 4 you must know exactly which files will need to be created or modified and why.

### Step 5 — Confirm the Test File Location and Name

Confirm the test file path: `C:\Users\HP\Desktop\AttendanceN\tempFolder_nominal\Book4_test for nominal roll.xlsx`. Verify it is accessible and that it matches the expected column structure defined in this prompt before using it for any test.

---

## EXCEL FILE STRUCTURE

The Nominal Roll file has a **single header row** (row 1). Data begins from row 2 onward.

All columns are resolved by **0-based index**. Do not rely on column names — column positions are authoritative. The table below defines every column in the file, whether to use or ignore it, and the exact mapping target.

### Column Mapping Table

| Col Index | Header Name | Action | Mapping Target |
|-----------|-------------|--------|----------------|
| 0 | S/N | **IGNORE** | — |
| 1 | Name | **USE** | `employees.full_name` (VARCHAR 255) |
| 2 | Sex | **USE** | `employees.sex` (VARCHAR 10) — store as-is; validate value is `M` or `F` |
| 3 | ID No. | **USE** | `employees.id_no` (VARCHAR 64) — **stored as integer in Excel; must be cast to string before storage** |
| 4 | Date of Birth | **IGNORE** | — |
| 5 | Qualifications with Dates | **IGNORE** | — |
| 6 | Professional Bodies | **IGNORE** | — |
| 7 | Professional Qualifications | **IGNORE** | — |
| 8 | Cadre | **IGNORE** | — |
| 9 | State of Origin | **IGNORE** | — |
| 10 | LGA | **IGNORE** | — |
| 11 | Geographical Zone | **USE** | `employees.geographical_zone` — see Schema Changes section |
| 12 | GL | **USE** | `employees.gl_id` → lookup/upsert `grade_levels.gl_name`; store GL value as string (e.g., `"17"`) |
| 13 | Step | **IGNORE** | — |
| 14 | Rank | **USE** | `employees.rank_id` → lookup/upsert `ranks.rank_name` |
| 15 | Department | **USE** | `employees.department_id` → lookup/upsert `departments.department_name` |
| 16 | Unit | **IGNORE** | — *(not in required column list; do not store)* |
| 17 | Location | **USE** | `employees.location_id` → lookup/upsert `locations.location_name` |
| 18 | Date of First Appt. | **IGNORE** | — |
| 19 | Date of Present Appt. | **IGNORE** | — |
| 20 | Date of Last Increment | **IGNORE** | — |
| 21 | Date of Previous Increment | **IGNORE** | — |
| 22 | Increment Cut Off | **IGNORE** | — |
| 23 | Increment Count | **IGNORE** | — |
| 24 | Applied Increment Count | **IGNORE** | — |
| 25 | Employment Type | **USE** | `employees.emp_type_id` → lookup `employment_types.emp_type_name`; **do not create new employment types unless the value is not found and is genuinely a new valid type — flag unknowns for review** |
| 26 | Status | **USE** | `employees.status_id` → lookup/upsert `employee_statuses.status_name` |
| 27 | Remark | **USE** | `employees.remark` (TEXT) — store `NULL` if empty, not an empty string |
| 28 | Date of Last Deployment | **USE** | `employees.date_of_last_deployment` — see Schema Changes section; stored as `DATE` |
| 29 | Residential Address | **IGNORE** | — |
| 30 | Residential State | **IGNORE** | — |

> **Critical ID No. handling:** The `ID No.` column (col 3) contains integer values in the Excel (e.g., `417`, `538`). The `employees.id_no` column is `character varying(64)`. You must convert the integer to a string (`str(int(value))`) before any lookup or insert. Never store it as a number. Never assume the Excel will always provide it as an integer — validate the cell type and handle string inputs too.

---

## REQUIRED DATABASE SCHEMA CHANGES

These are the schema changes required. **None of these may be applied until the full dependency audit from the Pre-Conditions section is complete and the plan has been reviewed.**

### 1. Remove `employees.serial_no`

The `serial_no` column (`serial NOT NULL`, `UNIQUE`) must be removed from the `employees` table. Before doing so:

- Search every table in the database for any foreign key referencing `employees.serial_no`. (Note: no FK to `serial_no` is visible in the current schema, but verify this — the primary key is `id_no`, not `serial_no`.)
- Search every file in the codebase for any reference to `serial_no` — in SQL queries, ORM models, API serializers, response formatters, tests, or comments.
- Document every reference found and what change is needed in each location.
- Only after all references are removed from the code and confirmed, drop the column with: `ALTER TABLE employees DROP COLUMN serial_no;`

### 2. Add `employees.geographical_zone`

Add a new column to store the Geographical Zone directly on the employee record:

```sql
ALTER TABLE employees ADD COLUMN geographical_zone character varying(100);
```

The value is read directly from col 11 of the Nominal Roll. It is stored as a plain string — no lookup table required unless you identify a clear need for one during your schema audit. Justify your decision in the plan.

### 3. Add `employees.date_of_last_deployment`

Add a new column for the Date of Last Deployment:

```sql
ALTER TABLE employees ADD COLUMN date_of_last_deployment DATE;
```

The value comes from col 28 of the Nominal Roll. It will be stored as an Excel serial date number in the raw file — it must be converted to a Python `date` object before storage. If the cell cannot be parsed as a date, store `NULL` and log a data quality warning.

### 4. Add `employees.phone_number`

Add a phone number column:

```sql
ALTER TABLE employees ADD COLUMN phone_number character varying(30);
```

This column defaults to `NULL` for all records until phone numbers are provided in a future data load. No phone number data exists in the current Nominal Roll file — do not attempt to populate it from any column.

### 5. History Tracking — Standardisation

The current schema has four separate history tables: `employee_department_history`, `employee_gl_history`, `employee_location_history`, `employee_rank_history`. Each follows the same pattern: `history_id`, `id_no`, `[field]_id`, `start_date`, `end_date`.

**Your task:** Propose in your plan a standardised, efficient approach for tracking changes to an employee's department, grade level, location, and rank over time. The system must support:
- Retrieving the full history of all departments a given staff member has ever been assigned to.
- Retrieving the full history of all locations, grade levels, and ranks similarly.
- Knowing the exact date a change became effective and, where applicable, when it ended.
- Efficient querying — it must be possible to find an employee's current values without scanning the entire history table.

Your plan must address: whether to keep the four separate tables or consolidate them, how the trigger/function logic that currently updates these tables will change, and what migration is needed for existing history data. **Do not apply any changes to these tables until the plan is approved.**

When a Nominal Roll file is processed and an employee's department, GL, location, or rank differs from their current value in the `employees` table, the old value must be written to the appropriate history table (with an `end_date` of today) before the `employees` table is updated. This must be atomic — use a database transaction for every employee record.

---

## UPSERT STRATEGY

The Nominal Roll is processed periodically. Every run may contain both new employees and updates to existing employees. The pipeline must handle both cases without duplicating records.

For each row in the Excel file:

1. **Look up the employee** in `employees` using `id_no` (converted to string).
2. **If the employee does not exist** → insert a new record. This is a new hire.
3. **If the employee already exists** → compare each mapped field against the current database value:
   - For `department_id`, `gl_id`, `location_id`, `rank_id`: if the value has changed, write the old value to the corresponding history table first, then update `employees`.
   - For `full_name`, `sex`, `status_id`, `emp_type_id`, `geographical_zone`, `date_of_last_deployment`, `remark`: update directly if changed — no history table required for these fields.
4. All inserts and updates for a single employee row must be wrapped in a **single database transaction**. If any part of the transaction fails, the entire row is rolled back and logged as a `FAILURE`.

---

## LOOKUP TABLE HANDLING

For each field that references a lookup table (`departments`, `grade_levels`, `locations`, `ranks`, `employment_types`, `employee_statuses`):

- Before processing any file, load the entire lookup table into an in-memory dictionary (`{name: id}`) for fast lookup during row processing.
- If a value from the Excel is **found** in the dictionary → use the corresponding ID.
- If a value is **not found**:
  - For `departments`, `grade_levels`, `locations`, `ranks`, `employee_statuses` → **insert the new value** into the lookup table, add it to the in-memory dictionary, and use the new ID. Log a data quality notice (not a warning) that a new lookup value was added.
  - For `employment_types` → **do not auto-insert**. Log a `FAILURE` for that row, flag the unknown employment type name clearly, and skip the row. Employment types are a controlled list and must not be auto-extended without human approval.
- After any new lookup insert, log the table name and the new value added.

---

## FILE PIPELINE — FULL END-TO-END FLOW

The goal of this task is a complete, working pipeline. Every stage listed below must be implemented, reviewed against the existing codebase, and updated to correctly handle Nominal Roll files.

### Stage 1 — File Detection (Inbox Watcher)

- The pipeline watches the `inbox` folder for new files.
- When a file is detected, it is passed to the file classifier.
- **The existing file classification logic must be reviewed and updated** to correctly route Nominal Roll files. State in your plan exactly what the current classifier does and what changes are needed.

### Stage 2 — File Classification & Type Identification

The classifier must identify a file as a Nominal Roll by checking for the following **column-position-based signatures** using 0-indexed positions (do not rely on the filename alone):

- Row 1 (0-indexed row 0), col 1 = `Name` (or close match — allow whitespace/casing variation)
- Row 1, col 3 = `ID No.`
- Row 1, col 11 = `Geographical Zone`
- Row 1, col 12 = `GL`
- Row 1, col 14 = `Rank`
- Row 1, col 15 = `Department`
- Row 1, col 17 = `Location`
- Row 1, col 25 = `Employment Type`
- Row 1, col 28 = `Date of Last Deployment`

If these signatures are not met, the file must not be treated as a Nominal Roll. Route it to the quarantine/rejection folder and log the mismatch with the specific column indices that failed.

### Stage 3 — Duplicate Detection

The existing duplicate-detection logic must be reviewed. For Nominal Roll files, a file should be considered a duplicate if a file with the same SHA-256 checksum has already been successfully processed (as recorded in `file_ingestion_meta`). Confirm how the `file_ingestion_meta` table's unique constraint (`checksum_sha256`, `department`, `report_type`, `period`) applies to Nominal Roll files and whether the `period` and `department` derivation from the normalized filename is correct for this file type. If the current logic does not handle Nominal Rolls correctly, fix it and document what changed.

### Stage 4 — Validation

Update the Nominal Roll validator to check:
- The column signature (as defined in Stage 2).
- That the file has at least one data row below the header.
- That the `ID No.` column (col 3) contains values for every data row (no blank `id_no` values — these are the primary key and cannot be null).
- That no two rows share the same `ID No.` value (duplicates within a single file are an error — log all duplicates and stop processing the file until resolved).

### Stage 5 — File Routing

After successful validation, the file must be moved from `inbox` to `Nominal_Folder`. Review the existing folder-routing logic and confirm it correctly handles Nominal Roll files. State in your plan what the current routing logic does and what changes are needed.

### Stage 6 — File Naming

When the file is placed in `Nominal_Folder`, it must be renamed according to the existing file-naming convention used by the system. Review the current naming logic and confirm it handles Nominal Roll files. If the convention does not yet cover Nominal Rolls, define the naming format in your plan and implement it consistently with the existing convention.

### Stage 7 — Data Extraction & Database Upsert

Process each data row according to the Column Mapping Table, Upsert Strategy, and Lookup Table Handling sections above.

### Stage 8 — Post-Processing

After all rows are processed:
- Update `file_ingestion_meta` to set `status = 'processed'` and `processed_at = now()`.
- Generate a processing summary report (see Error Logging section).
- Move the original file to its archive location if applicable.

---

## ERROR LOGGING REQUIREMENTS

Every row must produce one of three outcomes:

- **SUCCESS** — employee record created or updated, all history tables updated, no issues.
- **PARTIAL SUCCESS** — record processed but one or more data quality warnings were raised (e.g., a date field could not be parsed, a new lookup value was auto-inserted). Log the row number, field name, and description.
- **FAILURE** — row skipped entirely due to a critical error (e.g., blank `id_no`, unknown employment type, transaction rollback). Log the row number, the value of `id_no` if available, and the full error description.

At the end of each file run, generate a **processing summary report** containing:
- Filename processed and timestamp.
- Total rows read.
- Total employees created (new inserts).
- Total employees updated.
- Total history entries written (broken down by table).
- Total new lookup values added (broken down by table).
- Total warnings (by type and count).
- Total failures (by type and count).
- List of `id_no` values that failed, with reasons.

---

## PLAN REQUIREMENTS (Before Writing Any Code)

Produce a **detailed, structured written plan** that covers every item below. Implementation begins only after the plan is reviewed and approved.

1. **Full schema reproduction** — every table, every column, every constraint, every FK, as queried from the live database.
2. **Complete FK dependency map** — every table that references the tables the Nominal Roll populates, with ON UPDATE/ON DELETE behaviours.
3. **Full codebase audit** — every file that touches the Nominal Roll pipeline or references any of the affected tables or columns, with exact code snippets and the changes required in each.
4. **`serial_no` removal plan** — every reference found in DB and code, and the change required at each location.
5. **Schema additions plan** — exact `ALTER TABLE` statements for `geographical_zone`, `date_of_last_deployment`, `phone_number`, and any other required changes, with justification.
6. **History tracking redesign** — your proposed approach, the migration plan for existing history data, and the changes to any trigger/function logic.
7. **Upsert logic design** — how new vs. existing employees are distinguished, how field changes are detected, and how the transaction boundary is drawn.
8. **Lookup table strategy** — which tables auto-insert and which do not, and why.
9. **File pipeline update plan** — for each of the 8 stages above: current behaviour (with code reference), required changes, and how the change will be implemented.
10. **Testing plan** — a full breakdown of every test category and test case. See the dedicated Testing section below.

---

## TESTING REQUIREMENTS

### Test File — Scope and Boundaries

> ⚠️ **`Book4_test for nominal roll.xlsx` is a TEST FILE ONLY.**
>
> It is located at `C:\Users\HP\Desktop\AttendanceN\tempFolder_nominal\` and is used exclusively to validate the pipeline in a controlled test environment. It must never be processed directly as a production file. The codebase must always follow its normal file-intake processes — files are picked up from the `inbox` folder via the standard watcher. For testing, the test file must be routed through that same `inbox` path, not called directly. No special-case logic for this file is permitted anywhere in the codebase.

### Test Environment Setup

Before running any test:

1. Create a **test database** that is a structural clone of production — identical schema, same lookup table seed data, no production employee records.
2. Create a **test `inbox` folder** and a test `Nominal_Folder`, mirroring the production paths.
3. Seed the test database with a small set of known employee records (at least 5–10) with known values for `department_id`, `gl_id`, `location_id`, `rank_id`, etc., so that update detection and history tracking can be verified against known starting states.
4. Confirm all lookup tables (`departments`, `grade_levels`, `locations`, `ranks`, `employment_types`, `employee_statuses`) are seeded.
5. Confirm the test environment is fully isolated — no test should write to the production database or touch production folders under any circumstances.

---

### Test Category 1 — File Intake & Routing

| Test ID | Description | Input | Expected Outcome |
|---------|-------------|-------|-----------------|
| N-T1-01 | Valid Nominal Roll correctly identified | Test file dropped in test `inbox` | Classified as Nominal Roll; no other type assigned |
| N-T1-02 | Valid Nominal Roll moved to `Nominal_Folder` | Test file in `inbox` | File present in `Nominal_Folder`; removed from `inbox` |
| N-T1-03 | Non-Nominal file not misidentified | A Leave or Training file in `inbox` | File routed to its correct folder; Nominal pipeline not triggered |
| N-T1-04 | File missing signature columns is rejected | Excel without `Geographical Zone` at col 11 | File routed to quarantine; error logged with specific column mismatch |
| N-T1-05 | Duplicate file (same SHA-256) is handled | Same file submitted twice | Second run detected as duplicate; no records re-inserted; logged correctly |
| N-T1-06 | File with zero data rows is handled | Excel with header only | Pipeline exits cleanly; summary shows 0 rows; no crash |
| N-T1-07 | Corrupted file is handled | Invalid `.xlsx`-named file | Routed to quarantine; error logged; pipeline does not crash |

---

### Test Category 2 — Header & Column Parsing

| Test ID | Description | Expected Outcome |
|---------|-------------|-----------------|
| N-T2-01 | All 9 signature columns verified at correct indices | Log confirms each signature value and index |
| N-T2-02 | `ID No.` (col 3) read as integer and converted to string | Value `417` in Excel → `"417"` in database |
| N-T2-03 | Data rows begin at row 2 (0-indexed row 1) | Row 1 treated as header only; first employee extracted from row 2 |
| N-T2-04 | All IGNORE columns produce no database writes | Verify no data from cols 0, 4–10, 13, 16, 18–24, 29–30 appears anywhere in DB |

---

### Test Category 3 — New Employee Insertion

For a test row with an `id_no` not yet in the database:

| Test ID | Description | Expected Outcome |
|---------|-------------|-----------------|
| N-T3-01 | New employee row inserted correctly | Row exists in `employees` with all mapped fields correct |
| N-T3-02 | `full_name` stored correctly | Name from col 1 matches `employees.full_name` exactly |
| N-T3-03 | `sex` stored correctly | `M` or `F` stored in `employees.sex` |
| N-T3-04 | `id_no` stored as string | `employees.id_no = "417"`, not `417` |
| N-T3-05 | `geographical_zone` stored correctly | Value from col 11 in `employees.geographical_zone` |
| N-T3-06 | `gl_id` correctly resolved | GL value from col 12 → looked up in `grade_levels` → correct ID in `employees.gl_id` |
| N-T3-07 | `rank_id` correctly resolved | Rank from col 14 → looked up in `ranks` → correct ID |
| N-T3-08 | `department_id` correctly resolved | Department from col 15 → looked up in `departments` → correct ID |
| N-T3-09 | `location_id` correctly resolved | Location from col 17 → looked up in `locations` → correct ID |
| N-T3-10 | `emp_type_id` correctly resolved | Employment type from col 25 → looked up in `employment_types` → correct ID |
| N-T3-11 | `status_id` correctly resolved | Status from col 26 → looked up in `employee_statuses` → correct ID |
| N-T3-12 | `remark` stored as NULL when empty | Empty col 27 → `NULL` in `employees.remark`, not empty string |
| N-T3-13 | `remark` stored correctly when populated | Non-empty col 27 → correct string in `employees.remark` |
| N-T3-14 | `date_of_last_deployment` stored as DATE | Excel serial date from col 28 → converted to correct `DATE` value in DB |
| N-T3-15 | `phone_number` is NULL for all new records | `employees.phone_number = NULL` for every inserted row |
| N-T3-16 | No history table entries written for new employees | Verify `employee_department_history`, `employee_gl_history`, `employee_location_history`, `employee_rank_history` have no entries for the new `id_no` |

---

### Test Category 4 — Existing Employee Update & History Tracking

Seed a known employee record in the test database, then process a Nominal Roll row for the same `id_no` with changed values.

| Test ID | Field Changed | Expected Outcome |
|---------|--------------|-----------------|
| N-T4-01 | `department_id` changed | Old `department_id` written to `employee_department_history` with `end_date = today`; `employees.department_id` updated to new value |
| N-T4-02 | `gl_id` changed | Old `gl_id` written to `employee_gl_history` with `end_date = today`; `employees.gl_id` updated |
| N-T4-03 | `location_id` changed | Old `location_id` written to `employee_location_history` with `end_date = today`; `employees.location_id` updated |
| N-T4-04 | `rank_id` changed | Old `rank_id` written to `employee_rank_history` with `end_date = today`; `employees.rank_id` updated |
| N-T4-05 | No tracked fields changed | No history table entries written; `employees` record updated only for non-tracked fields that changed |
| N-T4-06 | Multiple tracked fields changed in one row | All changes written to history atomically; all `employees` fields updated |
| N-T4-07 | Transaction atomicity — simulated failure mid-row | DB is rolled back to state before the row was processed; no partial writes; failure logged |
| N-T4-08 | Full history retrieval after multiple runs | After 3 runs with different department values, query `employee_department_history` for that `id_no` → 2 completed history records + 1 open record in `employees.department_id` |

---

### Test Category 5 — Lookup Table Handling

| Test ID | Description | Expected Outcome |
|---------|-------------|-----------------|
| N-T5-01 | Known department value → lookup succeeds | Existing `department_id` used; no new row inserted into `departments` |
| N-T5-02 | Unknown department value → auto-insert | New row inserted into `departments`; new ID used in `employees`; data quality notice logged |
| N-T5-03 | Unknown GL value → auto-insert | New row inserted into `grade_levels`; new ID used |
| N-T5-04 | Unknown location value → auto-insert | New row inserted into `locations`; new ID used |
| N-T5-05 | Unknown rank value → auto-insert | New row inserted into `ranks`; new ID used |
| N-T5-06 | Unknown status value → auto-insert | New row inserted into `employee_statuses`; new ID used |
| N-T5-07 | Known employment type → lookup succeeds | Existing `emp_type_id` used; no new row inserted |
| N-T5-08 | Unknown employment type → row fails, not auto-inserted | `employment_types` unchanged; row logged as `FAILURE`; employee not inserted; pipeline continues to next row |

---

### Test Category 6 — Data Quality & Edge Cases

| Test ID | Description | Expected Outcome |
|---------|-------------|-----------------|
| N-T6-01 | `id_no` cell is blank | Row skipped; `FAILURE` logged with row number; pipeline continues |
| N-T6-02 | Duplicate `id_no` within same file | All duplicates flagged; processing halted with error listing all duplicate IDs; file not processed |
| N-T6-03 | `date_of_last_deployment` is not a parseable date | `NULL` stored; data quality warning logged with row and column index |
| N-T6-04 | `date_of_last_deployment` is an Excel serial number | Correctly converted to Python `date` before storage |
| N-T6-05 | `sex` value is neither `M` nor `F` | Stored as-is; data quality warning logged; row not failed |
| N-T6-06 | `id_no` stored as float in Excel (e.g., `417.0`) | Converted to `"417"` — the `.0` is stripped; verify with `str(int(float(value)))` |
| N-T6-07 | `remark` is whitespace only | Treated as empty → `NULL` stored |
| N-T6-08 | Very large file (500+ rows) | Pipeline completes without memory error; all rows processed; summary generated |

---

### Test Category 7 — Schema Change Verification

After all schema changes are applied to the test database, verify:

- [ ] `employees.serial_no` column does not exist.
- [ ] `employees.geographical_zone` column exists as `VARCHAR(100)`, nullable.
- [ ] `employees.date_of_last_deployment` column exists as `DATE`, nullable.
- [ ] `employees.phone_number` column exists as `VARCHAR(30)`, nullable.
- [ ] No foreign key in any table references `employees.serial_no`.
- [ ] All existing FK constraints to `employees.id_no` still exist and function correctly.
- [ ] All existing indexes remain intact.
- [ ] All four history tables remain structurally sound (or, if redesigned, the new structure supports all query requirements from the history tracking section).
- [ ] Run a full FK integrity check on the test database: `SELECT * FROM information_schema.referential_constraints` — confirm no orphaned constraints.

---

### Test Category 8 — `serial_no` Removal Verification

- [ ] No SQL query in the codebase references `serial_no`.
- [ ] No ORM model references `serial_no`.
- [ ] No API endpoint returns `serial_no` in its response.
- [ ] No test in the test suite references `serial_no`.
- [ ] No migration script attempts to insert `serial_no`.

---

### Test Category 9 — End-to-End Integration

Run the complete pipeline once, end-to-end, using the test file and test environment:

1. Drop the test file into the test `inbox` folder.
2. Trigger the pipeline via the normal watcher/scheduler — do not call the processing function directly.
3. Verify the file moves from `inbox` → `Nominal_Folder` with the correct renamed filename.
4. Verify `file_ingestion_meta` has a new record with `status = 'processed'`.
5. Verify the database state matches all expected outcomes from Categories 3–6.
6. Verify the processing summary report is generated, saved to the correct location, and contains accurate counts.
7. Confirm no production folders or database were touched.
8. Run a Leave file and a Training file through the pipeline simultaneously to confirm backward compatibility.

---

### Test Category 10 — Regression Testing

After all new code is in place and Categories 1–9 pass:

- Process a Leave file and confirm it still works correctly end-to-end.
- Process a Training file and confirm it still works correctly end-to-end.
- Process a Card Swipe file and confirm employee lookups (via `id_no`) still resolve correctly after the `serial_no` removal.
- Confirm any Kanban task assignee lookups via `employees.id_no` still function.
- If an existing automated test suite exists, run it in full and document any failures.

---

### Test Completion Criteria

The implementation is only considered **ready for production** when:

- [ ] All tests in Categories 1–10 have been run and results recorded.
- [ ] Zero tests in Categories 1–9 are failing.
- [ ] All Category 10 regression failures are resolved.
- [ ] The processing summary report from the end-to-end run shows correct counts with no unexplained failures.
- [ ] A test results document has been produced listing every test ID, input, expected outcome, actual outcome, and pass/fail verdict.
- [ ] The test database FK integrity check shows no orphaned constraints or broken references.

---

## IMPORTANT NOTES

- **No assumption is acceptable.** If anything in the codebase or schema is unclear, state it as a question in your plan and wait for clarification before proceeding.
- **No change is applied before the plan is reviewed and approved.** This includes schema changes, code changes, and test data insertion.
- **The Nominal Roll is the source of truth.** If the codebase and the Nominal Roll conflict on a value, the Nominal Roll wins — but the conflict must be flagged and documented.
- **`Book4_test for nominal roll.xlsx` is a test file only.** The codebase must always follow its normal intake and routing processes. No special-case logic for this file is permitted in the codebase.
- **All changes must be backward compatible.** Leave, Training, Card Swipe, and all other file-type pipelines must continue to function without modification after this task is complete.
- **Data types matter.** Every column must be stored in the correct type. Do not store dates as strings, integers as text without explicit conversion, or empty strings instead of `NULL`.
- **Transactions are non-negotiable.** Every employee record update — including any history table writes — must be wrapped in a single atomic transaction. Partial writes are worse than failures.
- **Take your time.** The cost of a mistake here propagates across the entire database and every pipeline that depends on it. Accuracy and completeness are more important than speed.
