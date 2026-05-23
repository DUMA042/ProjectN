# Leave File Data Processing — AI Agent Prompt (Optimized)

---

## ROLE & CONTEXT

Act as a **Senior Software Engineer with a strong Data Engineering background and deep Python expertise**. You are tasked with building a robust, production-grade pipeline that reads employee leave data from an Excel file and transfers it accurately into a relational database — with the minimum number of errors and full audit traceability.

---

## PRE-CONDITIONS (Do these BEFORE writing any code)

1. **Fully read and understand the existing database schema** — every table, every column, every foreign key constraint. Do not assume anything about the schema. Query it and confirm.
2. **Locate the `leave_types` table** in the database. All leave categories assigned to a staff record MUST reference this table by foreign key. Do not hardcode leave type names as strings in your logic.
3. **Locate the Leave File that will be use as a test case for you to build the full pipeline for it** in the `tempFolder` directory. Identify and confirm the exact sub-path it sits under `C:\Users\HP\Desktop\AttendanceN\tempFolder`. State this path clearly in your plan.
4. **Review the full existing codebase** — from the point the file lands in `inbox`, through the file-type detection stage, through the validator, to the final data-extraction step. You must update every stage that needs to change to reflect the new rules below.

---

## EXCEL FILE STRUCTURE

The Leave Excel file has **two header rows** (rows 1 and 2). Row 1 contains the major/group column headers; Row 2 contains sub-column headers. Data begins from row 3 onward.

Use the column mapping table below — columns are **0-indexed** to match programmatic access via `openpyxl` or `pandas`.

### Column Mapping Table

| Col Index | Row 1 Header (Major) | Row 2 Header (Sub) | Action |
|-----------|----------------------|--------------------|--------|
| 0 | — | S/N | **IGNORE** |
| 1 | — | NAMES | **IGNORE** |
| 2 | — | STAFF ID | **USE** — foreign key to staff table |
| 3 | — | GL  | **IGNORE** |
| 4 | — | DESIGNATION | **IGNORE** |
| 5 | — | LOCATION | **IGNORE** |
| 6 | — | PROPOSED LEAVE DATE | **USE** — see Proposed Leave Date rules below |
| 7 | — | RESUMPTION DATE | **USE** — see Proposed Leave Date rules below |
| 8 | PRE-RETIRMENT LEAVE | START DATE | **USE** → map to `Pre-Retirement Leave` |
| 9 | PRE-RETIREMENT LEAVE | END DATE | **USE** → map to `Pre-Retirement Leave` |
| 10 | CASUAL BEFORE ANNUAL | DURATION | **IGNORE** |
| 11 | CASUAL BEFORE ANNUAL | START DATE | **USE** → record as `Annual Leave` |
| 12 | CASUAL BEFORE ANNUAL | END DATE | **USE** → record as `Annual Leave` |
| 13 | CASUAL AFTER ANNUAL | DURATION | **IGNORE** |
| 14 | CASUAL AFTER ANNUAL | START DATE | **USE** → record as `Casual After Annual Leave` |
| 15 | CASUAL AFTER ANNUAL | END DATE | **USE** → record as `Casual After Annual Leave` |
| 16 | — | PART ANNUAL | **IGNORE** |
| 17 | — | ANNUAL LEAVE BALANCE | **IGNORE** |
| 18 | — | FORFEITURE | **IGNORE** |
| 19 | — | START DATE *(standalone)* | **USE** → Annual or Maternity — see Duration Rule below |
| 20 | — | END DATE *(standalone)* | **USE** → Annual or Maternity — see Duration Rule below |
| 21 | — | COMPASSIONATE LEAVE *(first occurrence — standalone value, not a major header)* | **IGNORE** |
| 22 | COMPASSIONATE LEAVE *(second occurrence — major header)* | START DATE | **USE** → map to `Compassionate Leave` |
| 23 | COMPASSIONATE LEAVE *(second occurrence)* | END DATE | **USE** → map to `Compassionate Leave` |
| 24 | PATERNITY LEAVE | PATERNITY LEAVE *(sub-value, not a date)* | **IGNORE** |
| 25 | PATERNITY LEAVE | START DATE | **USE** → map to `Paternity Leave` |
| 26 | PATERNITY LEAVE | END DATE | **USE** → map to `Paternity Leave` |
| 27 | — | MATERNITY LEAVE *(standalone value)* | **IGNORE** |
| 28 | — | SICK LEAVE *(first occurrence — standalone value)* | **IGNORE** |
| 29 | SICK LEAVE *(major header)* | START DATE | **USE** → map to `Sick Leave` |
| 30 | SICK LEAVE *(major header)* | END DATE | **USE** → map to `Sick Leave` |
| 31 | — | EXAM LEAVE *(first occurrence — standalone value)* | **IGNORE** |
| 32 | EXAM LEAVE *(major header)* | START DATE | **USE** → map to `Exam Leave` |
| 33 | EXAM LEAVE *(major header)* | END DATE | **USE** → map to `Exam Leave` |
| 34 | SUMMARY | LEAVE TYPE | **IGNORE** |
| 35 | SUMMARY | STATUS | **IGNORE** |
| 36 | — | UPDATE | **IGNORE** |
| 37 | STAFF FILE | REMARK | **USE** — store as a note/remark on the staff leave record |

> **Important:** When parsing the headers programmatically, do not rely on column names alone since several column names repeat (e.g., START DATE, END DATE, COMPASSIONATE LEAVE, EXAM LEAVE, SICK LEAVE appear multiple times). Always resolve columns by their **index position**, not by their name.

---

## BUSINESS RULES

### 1. Annual Leave vs. Maternity Leave — Columns 19 & 20

The standalone START DATE (col 19) and END DATE (col 20) serve double duty:

- Calculate the **working-day duration** between START DATE and END DATE.
- **If duration ≤ 30 working days → record as `Annual Leave`.**
- **If duration > 30 working days → record as `Maternity Leave`.**

**Working-day calculation plan (propose this in your report):**
- Exclude Saturdays and Sundays.
- Account for Nigerian public holidays. Explain where your holiday reference list will come from (hardcoded list, external API, or a database table) and how you will keep it current.
- If either date is missing or invalid, log an error for this row and skip this leave entry — do not guess.

### 2. Proposed Leave Date & Resumption Date — Columns 6 & 7

These two dates are **staff-level** (one pair per row) and represent the originally planned leave. However, because all leave records for a staff are on one row, and the Excel may not always be captured before a new leave overwrites the previous entry, the following mapping strategy applies:

**Recommended Strategy:**
- From all the leave entries successfully parsed for a given staff row (i.e., all leave types with valid start and end dates), **identify the leave whose START DATE is the latest (most recent)**.
- Map the PROPOSED LEAVE DATE and RESUMPTION DATE to that leave entry as its "planned" dates.
- Store both as separate fields (e.g., `planned_start_date`, `planned_end_date`) on that leave record so they can be compared against the actual start/end dates for analysis.
- **Do not discard** PROPOSED LEAVE DATE / RESUMPTION DATE even if no matching leave is found — store them at the staff-leave-snapshot level with a null `leave_type_id` if necessary, flagged for review.

**In your detailed plan, explicitly address:**
- How PROPOSED LEAVE DATE and RESUMPTION DATE will be stored in the database schema (new columns? separate table?).
- How the analysis comparing planned vs. actual leave will be supported by the schema.
- What happens when PROPOSED LEAVE DATE > all actual start dates (i.e., the planned leave has not been taken yet).

### 3. Date vs. String Handling — Columns 6 & 7 (and all date fields)

PROPOSED LEAVE DATE and RESUMPTION DATE (and potentially other date columns) may contain either:
- A valid date value, or
- A string (e.g., "PENDING", "N/A", "ON LEAVE", or free text).

**Rules:**
- Attempt to parse every date cell. Use `dateutil.parser.parse()` with a try/except as a fallback after `openpyxl`'s native date detection.
- If a cell is a recognised date → store as `DATE` type.
- If a cell is a string that cannot be parsed as a date → store the raw string in a separate `_raw_text` companion column (e.g., `proposed_leave_date_raw`) and set the date column to `NULL`.
- Check whether the existing codebase or database schema already handles this pattern. If it does, extend it consistently. If it does not, design the solution and document it.
- Log every row where a date field contains a non-date string as a **data quality warning** (not a hard error — the row should still be processed for other fields).

### 4. Leave Type Referencing

- Every leave entry recorded must reference the `leave_types` table by ID.
- Before processing any file, load the `leave_types` table into a dictionary (`{name: id}`) for fast lookup.
- If a required leave type name is not found in the table, **do not silently skip** — raise a configuration error that halts processing and logs the missing type name clearly. This forces the database to be corrected rather than silently dropping data.

### 5. Remark Column (col 37)

- Store the REMARK value against the staff's leave record for the processed file/period.
- If REMARK is empty or null, store `NULL` — do not store empty strings.

### 6. Empty / Null Leave Entries

- For any leave type where **both** START DATE and END DATE are empty/null, **skip that leave entry entirely** — do not insert a record with null dates.
- If only one of START DATE or END DATE is present (but not both), log a **data quality error** for that row and that leave type, and skip the entry.

---

## VALIDATION UPDATES

Review the existing file validator and update it to correctly identify a Leave File. The validator must check for the following **column-position-based signatures** (using 0-indexed positions), since column names alone are unreliable due to duplicates:

- Row 1, col 8 = `PRE- RETIREMENT LEAVE` (or close match — allow for minor whitespace/casing variation)
- Row 1, col 10 = `CASUAL BEFORE ANNUAL`
- Row 1, col 22 = `COMPASSIONATE LEAVE`
- Row 1, col 24 = `PATERNITY LEAVE`
- Row 2, col 2 = `STAFF ID`
- Row 2, col 6 = `PROPOSED LEAVE DATE`
- Row 2, col 7 = `RESUMPTION DATE`

If these signatures are not met, the file must **not** be treated as a Leave File. Log the mismatch clearly and route the file to a rejection/quarantine folder.

---

## ERROR LOGGING REQUIREMENTS

Every row processed must produce one of three outcomes:
1. **SUCCESS** — all applicable leave entries inserted without issue.
2. **PARTIAL SUCCESS** — row inserted but one or more leave entries had data quality issues (logged as warnings with row number, column index, and description).
3. **FAILURE** — row skipped entirely due to a critical error (e.g., STAFF ID not found in the staff table). Logged as an error.

At the end of each file run, generate a **processing summary report** that includes:
- Total rows read
- Total leave entries attempted
- Total leave entries successfully inserted
- Total warnings (by type)
- Total failures (by type)
- List of STAFF IDs that failed

---

## PLAN REQUIREMENTS (Before Writing Any Code)

Before implementing anything, produce a **detailed, structured written plan** that covers:

1. **Database schema review findings** — what tables exist, what columns exist, what needs to be added or modified.
2. **Codebase audit** — list every file/module that touches the Leave File pipeline from inbox to database insertion, and what changes each requires.
3. **Column parsing strategy** — how you will reliably resolve duplicate column names using index positions.
4. **Proposed Leave Date / Resumption Date strategy** — schema design + mapping logic with examples.
5. **Annual vs. Maternity classification** — working-day calculation approach including holiday handling.
6. **Date vs. string handling** — schema changes needed (if any) and parsing logic.
7. **Validator update plan** — exact signature checks to add.
8. **Error logging design** — where logs are stored, format, and how the summary report is generated.
9. **Testing plan** — how you will validate correctness using the provided test file (`Leave test file 2026_19.xlsx`) before running on production data. Note : this test may not have all the cases that are present in the production data.

**Only after the plan has been reviewed and approved should implementation begin.**

---

## IMPORTANT NOTES

- Do not add columns or rows to any database table unless explicitly requested or required by the plan above.
- Do not make assumptions about existing code — always read it first.
- Where you are uncertain about a business rule, flag it in your plan with a clear question rather than guessing.
- All changes must be **backward compatible** — other file types (Training, Nominal, etc.) must continue to work without modification.
- Take your time. Accuracy and clarity are more important than speed.
- The end goal is to use the plan to generate a full working pipeline for processing leave files. That means the process that goes on from the file being dropped in the inbox folder to the file moving into the Leave_Folder and then finally to the leave entries being inserted in the database.
- The file `Leave test file 2026_19.xlsx.xlsx` is a test file that can be used to validate the correctness of the plan.
