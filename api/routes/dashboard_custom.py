"""Dashboard custom endpoints — workforce status, leaderboard, employee summary."""
from fastapi import APIRouter, Query
from ui.lib.queries import (
    get_workforce_status,
    get_earliest_checkins,
    get_employee_summary,
)

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/workforce-status")
def workforce_status():
    df = get_workforce_status()
    return df.to_dict(orient="records")


@router.get("/dashboard/earliest-checkins")
def earliest_checkins(limit: int = Query(10, ge=1, le=50)):
    df = get_earliest_checkins(limit)
    return df.to_dict(orient="records")


@router.get("/dashboard/employee-summary")
def employee_summary():
    df = get_employee_summary()
    return df.to_dict(orient="records")
