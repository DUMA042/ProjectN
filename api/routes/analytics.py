"""Analytics endpoints — dashboard KPIs, department distribution, etc."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.dependencies import get_db
from owl.analyze.sql_queries import (
    get_dashboard_summary,
    get_department_distribution,
    get_leave_breakdown_by_type,
    get_recent_ingestions,
    get_status_distribution,
)

router = APIRouter(tags=["analytics"])


@router.get("/analytics/summary")
def analytics_summary(db: Session = Depends(get_db)):
    df = get_dashboard_summary(db)
    return df.to_dict(orient="records")[0] if not df.empty else {}


@router.get("/analytics/departments")
def analytics_departments(db: Session = Depends(get_db)):
    df = get_department_distribution(db)
    return df.to_dict(orient="records")


@router.get("/analytics/statuses")
def analytics_statuses(db: Session = Depends(get_db)):
    df = get_status_distribution(db)
    return df.to_dict(orient="records")


@router.get("/analytics/leave-breakdown")
def analytics_leave_breakdown(db: Session = Depends(get_db)):
    df = get_leave_breakdown_by_type(db)
    return df.to_dict(orient="records")


@router.get("/analytics/ingestions")
def analytics_ingestions(db: Session = Depends(get_db), limit: int = 20):
    df = get_recent_ingestions(db, limit=limit)
    return df.to_dict(orient="records")
