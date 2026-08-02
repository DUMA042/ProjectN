"""Leave analytics endpoints."""
from fastapi import APIRouter, Query
from ui.lib.queries import (
    get_leave_summary,
    get_leave_by_month,
    get_recent_leaves,
    get_leave_breakdown_by_type,
)

router = APIRouter(tags=["leave"])


@router.get("/leave/summary")
def leave_summary():
    df = get_leave_summary()
    return df.to_dict(orient="records")[0] if not df.empty else {}


@router.get("/leave/by-type")
def leave_by_type():
    df = get_leave_breakdown_by_type()
    return df.to_dict(orient="records")


@router.get("/leave/by-month")
def leave_by_month():
    df = get_leave_by_month()
    return df.to_dict(orient="records")


@router.get("/leave/recent")
def leave_recent(limit: int = Query(50, ge=1, le=500)):
    df = get_recent_leaves(limit)
    return df.to_dict(orient="records")
