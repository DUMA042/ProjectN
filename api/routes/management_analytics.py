"""Management analytics endpoints — flexible explore engine over the rule-driven
attendance fact table plus leave/training/employee data."""
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from owl.analytics.engine import get_dimension_options, run_explore
from owl.analytics.dimensions import dimensions_metadata
from owl.analytics.fact import rebuild_attendance_daily

router = APIRouter(tags=["management-analytics"])


class ExploreRequest(BaseModel):
    domain: str = "attendance"
    metrics: list[str] = []
    group_by: list[str] = []
    filters: dict[str, list[str]] = {}
    date_range: Optional[dict] = None
    compare: Optional[str] = None
    mode: str = "summary"
    page: int = 1
    page_size: int = 50
    sort_by: str = ""
    sort_dir: str = "desc"
    search: str = ""


@router.post("/analytics/explore")
def analytics_explore(body: ExploreRequest):
    try:
        return run_explore(
            domain=body.domain,
            metrics=body.metrics,
            group_by=body.group_by,
            filters=body.filters,
            date_range=body.date_range,
            compare=body.compare,
            mode=body.mode,
            page=body.page,
            page_size=body.page_size,
            sort_by=body.sort_by,
            sort_dir=body.sort_dir,
            search=body.search,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/analytics/dimensions")
def analytics_dimensions():
    return {
        "dimensions": dimensions_metadata(),
        "options": get_dimension_options(),
    }


@router.post("/analytics/refresh")
def analytics_refresh():
    meta = rebuild_attendance_daily()
    return {"status": "ok", **meta}


@router.get("/analytics/overview")
def analytics_overview():
    def totals(domain, metrics):
        return run_explore(domain=domain, metrics=metrics, group_by=[], page_size=1).get("totals", {})

    return {
        "employees": totals("employees", ["employees", "active"]),
        "attendance": totals("attendance", ["attendance_rate", "absence_rate", "coverage", "present_days", "absent_days"]),
        "leave": totals("leave", ["leave_records", "unique_staff"]),
        "training": totals("training", ["activities", "participants"]),
    }
