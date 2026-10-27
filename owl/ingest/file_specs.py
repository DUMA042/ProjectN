"""Descriptions of the Excel layouts the ingestion pipeline accepts.

Read-only metadata for the in-app "File formats" guide. Required positions are
imported from the validators/classifier so the guide cannot drift from what the
pipeline actually enforces. Nothing in the ingestion path imports this module
for processing, and no existing constant is modified.
"""
from __future__ import annotations

from owl.nominal.validator import NOMINAL_SIGNATURE

USAGE_REQUIRED = "required"
USAGE_OPTIONAL = "optional"
USAGE_IGNORED = "ignored"

POSITIONAL_WARNING = (
    "Columns are read by position. Do not insert, delete, or reorder columns."
)
LEAVE_POSITIONAL_WARNING = (
    "Leave files use two header rows and repeated header names — columns must "
    "stay in their exact positions."
)

_NOMINAL_HEADERS = (
    "S/N",
    "Name",
    "Sex",
    "ID No.",
    "Date of Birth",
    "Qualifications with Dates",
    "Professional Bodies",
    "Professional Qualifications",
    "Cadre",
    "State of Origin",
    "LGA",
    "Geographical Zone",
    "GL",
    "Step",
    "Rank",
    "Department",
    "Unit",
    "Location",
    "Date of First Appt.",
    "Date of Present Appt.",
    "Date of Last Increment",
    "Date of Previous Increment",
    "Increment Cut Off",
    "Increment Count",
    "Applied Increment Count",
    "Employment Type",
    "Status",
    "Remark",
    "Date of Last Deployment",
    "Residential Address",
    "Residential State",
)

# Positional columns the pipeline reads that are not part of the header
# signature (sex, status, remark).
_NOMINAL_EXTRA_REQUIRED = {2, 26, 27}

_NOMINAL_NOTES = {
    2: "M or F",
    3: "Stored as text — numbers are converted automatically",
    11: "Free text",
    12: "Grade level, e.g. 08",
    25: "Must match an existing employment type",
    26: "Must match an existing status",
    27: "Optional content, but the column must be present",
    28: "Date of last deployment",
}

# Leave: (index, row-1 major header, row-2 sub header, usage, note)
_LEAVE_COLUMNS = [
    (0, "", "S/N", USAGE_IGNORED, ""),
    (1, "", "NAMES", USAGE_IGNORED, ""),
    (2, "", "STAFF ID", USAGE_REQUIRED, "Must match an employee ID"),
    (3, "", "GL", USAGE_IGNORED, ""),
    (4, "", "DESIGNATION", USAGE_IGNORED, ""),
    (5, "", "LOCATION", USAGE_IGNORED, ""),
    (6, "", "PROPOSED LEAVE DATE", USAGE_REQUIRED, "Start of the leave"),
    (7, "", "RESUMPTION DATE", USAGE_REQUIRED, "End/resumption date"),
    (8, "PRE-RETIREMENT LEAVE", "START DATE", USAGE_REQUIRED, "Pre-Retirement leave"),
    (9, "PRE-RETIREMENT LEAVE", "END DATE", USAGE_REQUIRED, "Pre-Retirement leave"),
    (10, "CASUAL BEFORE ANNUAL", "DURATION", USAGE_IGNORED, ""),
    (11, "CASUAL BEFORE ANNUAL", "START DATE", USAGE_REQUIRED, "Recorded as Annual leave"),
    (12, "CASUAL BEFORE ANNUAL", "END DATE", USAGE_REQUIRED, "Recorded as Annual leave"),
    (13, "CASUAL AFTER ANNUAL", "DURATION", USAGE_IGNORED, ""),
    (14, "CASUAL AFTER ANNUAL", "START DATE", USAGE_REQUIRED, "Casual After Annual leave"),
    (15, "CASUAL AFTER ANNUAL", "END DATE", USAGE_REQUIRED, "Casual After Annual leave"),
    (16, "", "PART ANNUAL", USAGE_IGNORED, ""),
    (17, "", "ANNUAL LEAVE BALANCE", USAGE_IGNORED, ""),
    (18, "", "FORFEITURE", USAGE_IGNORED, ""),
    (19, "", "START DATE (standalone)", USAGE_REQUIRED, "Annual or Maternity leave"),
    (20, "", "END DATE (standalone)", USAGE_REQUIRED, "Annual or Maternity leave"),
    (21, "", "COMPASSIONATE LEAVE (standalone)", USAGE_IGNORED, ""),
    (22, "COMPASSIONATE LEAVE", "START DATE", USAGE_REQUIRED, "Compassionate leave"),
    (23, "COMPASSIONATE LEAVE", "END DATE", USAGE_REQUIRED, "Compassionate leave"),
    (24, "PATERNITY LEAVE", "PATERNITY LEAVE", USAGE_IGNORED, ""),
    (25, "PATERNITY LEAVE", "START DATE", USAGE_REQUIRED, "Paternity leave"),
    (26, "PATERNITY LEAVE", "END DATE", USAGE_REQUIRED, "Paternity leave"),
    (27, "", "MATERNITY LEAVE (standalone)", USAGE_IGNORED, ""),
    (28, "", "SICK LEAVE (standalone)", USAGE_IGNORED, ""),
    (29, "SICK LEAVE", "START DATE", USAGE_REQUIRED, "Sick leave"),
    (30, "SICK LEAVE", "END DATE", USAGE_REQUIRED, "Sick leave"),
    (31, "", "EXAM LEAVE (standalone)", USAGE_IGNORED, ""),
    (32, "EXAM LEAVE", "START DATE", USAGE_REQUIRED, "Exam leave"),
    (33, "EXAM LEAVE", "END DATE", USAGE_REQUIRED, "Exam leave"),
    (34, "SUMMARY", "LEAVE TYPE", USAGE_IGNORED, ""),
    (35, "SUMMARY", "STATUS", USAGE_IGNORED, ""),
    (36, "", "UPDATE", USAGE_IGNORED, ""),
    (37, "STAFF FILE", "REMARK", USAGE_REQUIRED, "Stored as a remark on the leave record"),
]


def _nominal_columns() -> list[dict]:
    required = set(NOMINAL_SIGNATURE) | _NOMINAL_EXTRA_REQUIRED
    return [
        {
            "index": index,
            "header": header,
            "usage": USAGE_REQUIRED if index in required else USAGE_IGNORED,
            "note": _NOMINAL_NOTES.get(index, ""),
        }
        for index, header in enumerate(_NOMINAL_HEADERS)
    ]


def _leave_columns() -> list[dict]:
    return [
        {
            "index": index,
            "header": sub,
            "group": group,
            "usage": usage,
            "note": note,
        }
        for index, group, sub, usage, note in _LEAVE_COLUMNS
    ]


def build_file_specs() -> dict:
    """Return the file-layout reference served to the upload page."""
    nominal_required = sorted(
        {c["index"] for c in _nominal_columns() if c["usage"] == USAGE_REQUIRED}
    )
    training_required = ["id_no", "venue", "consultant", "start_date"]
    swipe_required = ["name", "card_swiping_time"]

    return {
        "types": [
            {
                "id": "nominal",
                "label": "Nominal Roll",
                "accepted": ".xlsx",
                "header_rows": 1,
                "data_starts_row": 2,
                "min_columns": 29,
                "positional": True,
                "detection": "Identified by headers at positions 1, 3, 11, 12, 14, 15, 17, 25 and 28.",
                "filename_example": "AHRD_Nominal_202610_v1.xlsx",
                "required_indexes": nominal_required,
                "columns": _nominal_columns(),
                "warnings": [POSITIONAL_WARNING],
            },
            {
                "id": "leave",
                "label": "Leave",
                "accepted": ".xlsx",
                "header_rows": 2,
                "data_starts_row": 3,
                "min_columns": 38,
                "positional": True,
                "detection": "Two header rows; STAFF ID must be at position 2.",
                "filename_example": "AHRD_Leave_202610_v1.xlsx",
                "required_indexes": [
                    c["index"] for c in _leave_columns() if c["usage"] == USAGE_REQUIRED
                ],
                "columns": _leave_columns(),
                "warnings": [LEAVE_POSITIONAL_WARNING],
            },
            {
                "id": "training",
                "label": "Training",
                "accepted": ".xlsx",
                "header_rows": 1,
                "data_starts_row": 2,
                "min_columns": None,
                "positional": False,
                "detection": "Identified by the columns venue, consultant and start_date.",
                "filename_example": "AHRD_Training_202610_v1.xlsx",
                "required_indexes": [],
                "required_headers": training_required,
                "columns": [
                    {
                        "index": None,
                        "header": "id_no (or id / staff_id / staffid / employee_id)",
                        "usage": USAGE_REQUIRED,
                        "note": "Must match an employee ID",
                    },
                    {
                        "index": None,
                        "header": "venue",
                        "usage": USAGE_REQUIRED,
                        "note": "",
                    },
                    {
                        "index": None,
                        "header": "consultant",
                        "usage": USAGE_REQUIRED,
                        "note": "",
                    },
                    {
                        "index": None,
                        "header": "start_date",
                        "usage": USAGE_REQUIRED,
                        "note": "",
                    },
                    {
                        "index": None,
                        "header": "end_date",
                        "usage": USAGE_OPTIONAL,
                        "note": "",
                    },
                    {
                        "index": None,
                        "header": "title",
                        "usage": USAGE_OPTIONAL,
                        "note": "",
                    },
                    {
                        "index": None,
                        "header": "location",
                        "usage": USAGE_OPTIONAL,
                        "note": "",
                    },
                ],
                "warnings": [
                    "Training files may be matched by column name, but headers must be on one of the first ten rows."
                ],
            },
            {
                "id": "card_swipe",
                "label": "Card Swipe",
                "accepted": ".xlsx",
                "header_rows": 1,
                "data_starts_row": 2,
                "min_columns": None,
                "positional": False,
                "detection": "Identified by the column card_swiping_time.",
                "filename_example": "AHRD_CardSwipe_202610_v1.xlsx",
                "required_indexes": [],
                "required_headers": swipe_required,
                "columns": [
                    {
                        "index": None,
                        "header": "name",
                        "usage": USAGE_REQUIRED,
                        "note": "Matched to an employee by name",
                    },
                    {
                        "index": None,
                        "header": "card_swiping_time",
                        "usage": USAGE_REQUIRED,
                        "note": "attendance_time is also accepted",
                    },
                    {
                        "index": None,
                        "header": "attendance_terminal",
                        "usage": USAGE_OPTIONAL,
                        "note": "Used as the swipe location",
                    },
                    {
                        "index": None,
                        "header": "location",
                        "usage": USAGE_OPTIONAL,
                        "note": "",
                    },
                ],
                "warnings": [
                    "Swipe times are matched to employees by name; unmatched names are quarantined."
                ],
            },
        ],
        "filename_pattern": "DEPT_TYPE_YYYYMM_vN.xlsx",
        "note": "Files are renamed automatically after upload. Only .xlsx files are accepted.",
    }


FILE_SPECS = build_file_specs()
