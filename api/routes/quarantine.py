"""Quarantine endpoints — global explorer for orphaned rows.

Covers quarantine_card_swipes and quarantine_trainings tables with
filtering, pagination, CSV-ready listing, bulk delete, and reprocess
(attempt to resolve rows against the current employees table and load
them into their real destination tables).
"""
from __future__ import annotations

import re
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, or_

from api.dependencies import get_db
from owl.load.models import (
    Consultant,
    Employee,
    EmployeeCardSwipe,
    EmployeeTraining,
    Location,
    QuarantineCardSwipe,
    QuarantineTraining,
    Venue,
)

router = APIRouter(tags=["quarantine"])


# ── Shared helpers ────────────────────────────────────────────────────────────

def _normalise_name(s: str) -> str:
    return " ".join(str(s).lower().strip().split())


def _sorted_parts(s: str) -> str:
    return " ".join(sorted(re.sub(r"[^\w\s]", "", str(s).lower()).split()))


def _build_name_maps(session) -> tuple[dict, dict]:
    """Return (name_to_id, sorted_key_to_id) from current employees."""
    name_to_id: dict[str, str] = {}
    sorted_to_id: dict[str, str] = {}
    for id_no, full_name in session.execute(select(Employee.id_no, Employee.full_name)).all():
        if not full_name:
            continue
        clean = _normalise_name(full_name)
        name_to_id[clean] = id_no
        sorted_to_id[_sorted_parts(full_name)] = id_no
    return name_to_id, sorted_to_id


def _resolve_employee(session, name: str, name_to_id: dict, sorted_to_id: dict) -> Optional[str]:
    """Try exact then sorted-parts matching. Returns id_no or None."""
    clean = _normalise_name(name)
    if clean in name_to_id:
        return name_to_id[clean]
    return sorted_to_id.get(_sorted_parts(name))


def _get_or_insert(model_class, name_attr: str, id_attr: str, name_value: Optional[str], session):
    """Lookup a dimension row by name; insert when missing. Returns id or None."""
    if not name_value or str(name_value).strip().lower() in ("", "none", "nan", "unknown"):
        return None
    clean = str(name_value).strip()
    existing = session.execute(
        select(model_class).where(getattr(model_class, name_attr) == clean)
    ).scalars().first()
    if existing:
        return getattr(existing, id_attr)
    obj = model_class(**{name_attr: clean})
    session.add(obj)
    session.flush()
    return getattr(obj, id_attr)


# ── Listing ───────────────────────────────────────────────────────────────────

@router.get("/quarantine")
def list_quarantine(
    type: str = Query("swipes", pattern="^(swipes|trainings)$"),
    search: str = Query("", max_length=120),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db=Depends(get_db),
):
    params: dict = {}
    conditions = []

    if search.strip():
        params["search"] = f"%{search.strip().lower()}%"
        if type == "swipes":
            conditions.append(
                "(LOWER(COALESCE(employee_name, '')) LIKE :search "
                "OR LOWER(COALESCE(location_name, '')) LIKE :search)"
            )
        else:
            conditions.append(
                "(LOWER(COALESCE(id_no, '')) LIKE :search "
                "OR LOWER(COALESCE(venue_name, '')) LIKE :search "
                "OR LOWER(COALESCE(consultant_name, '')) LIKE :search "
                "OR LOWER(COALESCE(title, '')) LIKE :search)"
            )

    if type == "swipes":
        date_col = "swipe_time"
    else:
        date_col = "start_date"

    if start_date:
        params["start_date"] = start_date
        conditions.append(f"COALESCE({date_col}::date) >= :start_date")
    if end_date:
        params["end_date"] = end_date
        conditions.append(f"COALESCE({date_col}::date) <= :end_date")

    where_sql = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    if type == "swipes":
        base_table = "quarantine_card_swipes"
    else:
        base_table = "quarantine_trainings"

    from sqlalchemy import text

    count_sql = f"SELECT COUNT(*) FROM {base_table} {where_sql}"
    total = db.execute(text(count_sql), params).scalar() or 0

    offset = (page - 1) * size
    if type == "swipes":
        data_sql = f"""
            SELECT id, COALESCE(id_no, '') AS row_key, employee_name,
                   location_name, swipe_time, quarantined_at
            FROM {base_table} {where_sql}
            ORDER BY quarantined_at DESC
            LIMIT :limit OFFSET :offset
        """
    else:
        data_sql = f"""
            SELECT id, COALESCE(id_no, '') AS row_key, venue_name,
                   consultant_name, title, start_date, end_date, quarantined_at
            FROM {base_table} {where_sql}
            ORDER BY quarantined_at DESC
            LIMIT :limit OFFSET :offset
        """

    rows_raw = db.execute(
        text(data_sql), {**params, "limit": size, "offset": offset}
    ).mappings().all()

    distinct_names = 0
    if type == "swipes":
        distinct_names = db.execute(
            text(f"SELECT COUNT(DISTINCT employee_name) FROM {base_table}")
        ).scalar() or 0

    return {
        "type": type,
        "total": int(total),
        "page": page,
        "size": size,
        "distinct_names": distinct_names,
        "rows": [
            {
                "id": r["id"],
                "row_key": r.get("row_key", ""),
                "employee_name": r.get("employee_name") or r.get("row_key"),
                "location": r.get("location_name"),
                "venue": r.get("venue_name"),
                "consultant": r.get("consultant_name"),
                "title": r.get("title"),
                "start_date": r.get("start_date").isoformat() if r.get("start_date") else None,
                "end_date": r.get("end_date").isoformat() if r.get("end_date") else None,
                "event_time": r.get("swipe_time").isoformat() if r.get("swipe_time") else None,
                "quarantined_at": r.get("quarantined_at").isoformat() if r.get("quarantined_at") else None,
            }
            for r in rows_raw
        ],
    }


# ── Delete ────────────────────────────────────────────────────────────────────

class QuarantineIdsRequest(BaseModel):
    ids: List[int]


@router.delete("/quarantine/{type}")
def delete_quarantine(type: str, body: QuarantineIdsRequest, db=Depends(get_db)):
    if type not in ("swipes", "trainings"):
        raise HTTPException(status_code=400, detail="type must be 'swipes' or 'trainings'")
    if not body.ids:
        raise HTTPException(status_code=400, detail="No IDs provided")

    model_class = QuarantineCardSwipe if type == "swipes" else QuarantineTraining
    deleted = db.execute(
        model_class.__table__.delete().where(model_class.id.in_(body.ids))
    ).rowcount
    db.commit()
    return {"status": "ok", "deleted": deleted}


# ── Reprocess ────────────────────────────────────────────────────────────────

@router.post("/quarantine/reprocess")
def reprocess_quarantine(body: QuarantineIdsRequest, type: str = Query("swipes"), db=Depends(get_db)):
    """Attempt to resolve quarantined rows against the current employees
    table and move them into their real destination tables.

    - swipes:   match employee_name → employees (exact + sorted-parts);
                on success insert into employee_card_swipes.
    - trainings: check stored id_no now exists in employees;
                on success insert into employee_trainings.
    Rows that still cannot be resolved are left untouched and reported.
    """
    if type not in ("swipes", "trainings"):
        raise HTTPException(status_code=400, detail="type must be 'swipes' or 'trainings'")
    if not body.ids:
        raise HTTPException(status_code=400, detail="No IDs provided")

    succeeded = 0
    failures: list[dict] = []
    results: list[dict] = []

    name_to_id, sorted_to_id = _build_name_maps(db)

    if type == "swipes":
        rows = db.execute(
            select(QuarantineCardSwipe).where(QuarantineCardSwipe.id.in_(body.ids))
        ).scalars().all()

        for q in rows:
            try:
                emp_id = _resolve_employee(db, q.employee_name or "", name_to_id, sorted_to_id)
                if not emp_id:
                    msg = f"Employee '{q.employee_name}' still not found — add them first."
                    failures.append({"id": q.id, "error": msg})
                    results.append({"id": q.id, "ok": False, "error": msg})
                    continue

                location_id = _get_or_insert(Location, "location_name", "location_id", q.location_name, db)
                db.add(EmployeeCardSwipe(
                    id_no=emp_id,
                    location_id=location_id,
                    swipe_time=q.swipe_time,
                ))
                db.delete(q)
                succeeded += 1
                results.append({"id": q.id, "ok": True})
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                msg = f"Reprocess failed: {exc}"
                failures.append({"id": q.id, "error": msg})
                results.append({"id": q.id, "ok": False, "error": msg})

    else:
        rows = db.execute(
            select(QuarantineTraining).where(QuarantineTraining.id.in_(body.ids))
        ).scalars().all()

        valid_ids = set(db.execute(select(Employee.id_no)).scalars().all())

        for q in rows:
            try:
                if q.id_no not in valid_ids:
                    msg = f"Employee '{q.id_no}' still not found — add them first."
                    failures.append({"id": q.id, "error": msg})
                    results.append({"id": q.id, "ok": False, "error": msg})
                    continue

                venue_id = _get_or_insert(Venue, "venue_name", "venue_id", q.venue_name, db)
                consultant_id = _get_or_insert(Consultant, "consultant_name", "consultant_id", q.consultant_name, db)
                db.add(EmployeeTraining(
                    id_no=q.id_no,
                    venue_id=venue_id,
                    consultant_id=consultant_id,
                    start_date=q.start_date,
                    end_date=q.end_date,
                    title=q.title,
                ))
                db.delete(q)
                succeeded += 1
                results.append({"id": q.id, "ok": True})
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                msg = f"Reprocess failed: {exc}"
                failures.append({"id": q.id, "error": msg})
                results.append({"id": q.id, "ok": False, "error": msg})

    db.commit()
    return {
        "status": "ok",
        "succeeded": succeeded,
        "failed_count": len(failures),
        "failures": failures,
        "results": results,
    }
