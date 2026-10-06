"""Column detection + vault-token hashing for Build-section CSV copies.

Sensitive columns are replaced with stable vault tokens (see owl.privacy.vault)
in a NEW file — originals are never modified. Consistent tokens preserve
cross-file joins and ID grouping when only names are hashed.
"""
from __future__ import annotations

import csv
import io
import re

from sqlalchemy.orm import Session

from api.routes.report_inbox import ID_HEADERS, header_cells
from owl.privacy.vault import get_or_create_tokens

HASH_MODES = ("names_only", "names_and_ids")

# Normalized headers treated as the employee-name column. Equality match only
# (same discipline as ID_HEADERS): "department name" normalizes to
# "departmentname" and does NOT match.
NAME_HEADERS = {"fullname", "employeename", "name", "staffname"}


def norm_header(h: object) -> str:
    return re.sub(r"[\s_]+", "", str(h).strip().lower())


def detect_sensitive_columns(csv_text: str) -> dict[str, int | None]:
    """First matching name/ID column indexes (None when absent)."""
    headers = header_cells(csv_text)
    name_idx: int | None = None
    id_idx: int | None = None
    for i, h in enumerate(headers):
        n = norm_header(h)
        if name_idx is None and n in NAME_HEADERS:
            name_idx = i
        if id_idx is None and n in ID_HEADERS:
            id_idx = i
    return {"name_idx": name_idx, "id_idx": id_idx}


def hash_csv_text(
    session: Session, csv_text: str, mode: str
) -> tuple[str, dict[str, int]]:
    """Return (hashed_csv_text, stats) with vault tokens in sensitive columns.

    mode "names_only" tokenizes the name column; "names_and_ids" tokenizes
    both name and ID columns. Blanks pass through untouched. Raises
    ValueError on bad mode, missing columns for the mode, or vault limits.
    """
    if mode not in HASH_MODES:
        raise ValueError(f"Unknown hash mode '{mode}' (expected one of {HASH_MODES})")
    cols = detect_sensitive_columns(csv_text)
    if cols["name_idx"] is None:
        raise ValueError("No employee-name column found to hash")
    if mode == "names_and_ids" and cols["id_idx"] is None:
        raise ValueError("No employee-ID column found to hash")

    reader = csv.reader(io.StringIO(csv_text.lstrip("\ufeff")))
    rows = list(reader)
    if not rows:
        raise ValueError("Empty CSV content")
    header, body = rows[0], rows[1:]

    name_idx = cols["name_idx"]
    assert name_idx is not None
    names = [r[name_idx] if name_idx < len(r) else "" for r in body]
    name_map = get_or_create_tokens(session, "name", names)

    id_map: dict[str, str] = {}
    id_idx = cols["id_idx"] if mode == "names_and_ids" else None
    if id_idx is not None:
        ids = [r[id_idx] if id_idx < len(r) else "" for r in body]
        id_map = get_or_create_tokens(session, "id", ids)

    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(header)
    names_hashed = ids_hashed = 0
    for r, nm in zip(body, names):
        row = list(r)
        if nm.strip():
            row[name_idx] = name_map[nm]
            names_hashed += 1
        if id_idx is not None:
            iv = r[id_idx] if id_idx < len(r) else ""
            if iv.strip():
                row[id_idx] = id_map[iv]
                ids_hashed += 1
        writer.writerow(row)
    return out.getvalue(), {"names_hashed": names_hashed, "ids_hashed": ids_hashed}
