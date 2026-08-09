"""Dashboard custom endpoints — workforce status, dept attendance, employee summary, locations, arrival time."""
from fastapi import APIRouter, Query
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
):
    df = get_earliest_checkins(start_date, end_date, limit, location)
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
):
    df = get_employee_summary(start_date, end_date, location)
    return df.to_dict(orient="records")


