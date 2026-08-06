"""Dashboard custom endpoints — workforce status, dept attendance, employee summary."""
from fastapi import APIRouter, Query
from ui.lib.queries import (
    get_workforce_status,
    get_dept_attendance,
    get_earliest_checkins,
    get_employee_summary,
    get_departments,
)

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/workforce-status")
def workforce_status(
    start_date: str = Query(..., description="Start date YYYY-MM-DD"),
    end_date: str = Query(..., description="End date YYYY-MM-DD"),
    department: str = Query("", description="Department filter"),
):
    df = get_workforce_status(start_date, end_date, department)
    return df.to_dict(orient="records")


@router.get("/dashboard/dept-attendance")
def dept_attendance(
    start_date: str = Query(..., description="Start date YYYY-MM-DD"),
    end_date: str = Query(..., description="End date YYYY-MM-DD"),
    department: str = Query("", description="Department filter"),
):
    df = get_dept_attendance(start_date, end_date, department)
    return df.to_dict(orient="records")


@router.get("/dashboard/earliest-checkins")
def earliest_checkins(
    start_date: str = Query(..., description="Start date YYYY-MM-DD"),
    end_date: str = Query(..., description="End date YYYY-MM-DD"),
    limit: int = Query(10, ge=1, le=50),
):
    df = get_earliest_checkins(start_date, end_date, limit)
    return df.to_dict(orient="records")


@router.get("/dashboard/employee-summary")
def employee_summary():
    df = get_employee_summary()
    return df.to_dict(orient="records")


@router.get("/dashboard/departments")
def dashboard_departments():
    return get_departments()

