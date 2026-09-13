"""Dashboard custom endpoints — workforce status, dept attendance, employee summary, locations, arrival time."""
import json
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from ui.lib.queries import (
    get_workforce_status,
    get_dept_attendance,
    get_earliest_checkins,
    get_employee_summary,
    get_departments,
    get_locations,
    get_arrival_time,
)

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/locations")
def dashboard_locations():
    return get_locations()


@router.get("/dashboard/departments")
def dashboard_departments(
    location: str = Query("", description="Location filter"),
):
    return get_departments(location)


@router.get("/dashboard/workforce-status")
def workforce_status(
    start_date: str = Query(..., description="Start date YYYY-MM-DD"),
    end_date: str = Query(..., description="End date YYYY-MM-DD"),
    department: str = Query("", description="Department filter"),
    location: str = Query("", description="Location filter"),
):
    df = get_workforce_status(start_date, end_date, department, location)
    return df.to_dict(orient="records")


@router.get("/dashboard/dept-attendance")
def dept_attendance(
    start_date: str = Query(..., description="Start date YYYY-MM-DD"),
    end_date: str = Query(..., description="End date YYYY-MM-DD"),
    department: str = Query("", description="Department filter"),
    location: str = Query("", description="Location filter"),
):
    df = get_dept_attendance(start_date, end_date, department, location)
    return df.to_dict(orient="records")


@router.get("/dashboard/earliest-checkins")
def earliest_checkins(
    start_date: str = Query(..., description="Start date YYYY-MM-DD"),
    end_date: str = Query(..., description="End date YYYY-MM-DD"),
    limit: int = Query(10, ge=1, le=50),
    location: str = Query("", description="Location filter"),
    mode: str = Query("avg_checkin", description="avg_checkin or top_arrivals"),
):
    if mode not in ("avg_checkin", "top_arrivals"):
        raise HTTPException(status_code=422, detail="mode must be 'avg_checkin' or 'top_arrivals'")
    df = get_earliest_checkins(start_date, end_date, limit, location, mode)
    return df.to_dict(orient="records")


@router.get("/dashboard/arrival-time")
def arrival_time(
    start_date: str = Query(..., description="Start date YYYY-MM-DD"),
    end_date: str = Query(..., description="End date YYYY-MM-DD"),
    department: str = Query("", description="Department filter"),
    location: str = Query("", description="Location filter"),
):
    df = get_arrival_time(start_date, end_date, department, location)
    return df.to_dict(orient="records")


@router.get("/dashboard/employee-summary")
def employee_summary(
    start_date: str = Query("", description="Start date YYYY-MM-DD"),
    end_date: str = Query("", description="End date YYYY-MM-DD"),
    location: str = Query("", description="Location filter"),
    page: int = Query(1, ge=1, description="1-based page number"),
    page_size: int = Query(25, ge=0, le=10000, description="Rows per page; 0 = all (export)"),
    search: str = Query("", description="Global search string"),
    sort_by: str = Query("full_name", description="Column to sort by"),
    sort_dir: str = Query("asc", description="asc or desc"),
    filters: str = Query("", description="JSON object of {column: [values]}"),
):
    try:
        parsed_filters = json.loads(filters) if filters else {}
    except Exception:
        parsed_filters = {}
    return get_employee_summary(
        start_date, end_date, location,
        page=page, page_size=page_size, search=search,
        sort_by=sort_by, sort_dir=sort_dir, filters=parsed_filters,
    )


