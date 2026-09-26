"""Management analytics endpoints — flexible explore engine over the rule-driven
attendance fact table plus leave/training/employee data, plus the unified
metric catalog, today snapshot, signal engine and forecast layer."""
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from owl.analytics.engine import get_dimension_options, run_explore
from owl.analytics.dimensions import dimensions_metadata
from owl.analytics.fact import rebuild_attendance_daily
from owl.analytics.forecast import build_forecast
from owl.analytics.metrics import METRIC_DOMAINS, metrics_catalog
from owl.analytics.signals import compute_signals
from owl.analytics.today import freshness_snapshot, today_snapshot

router = APIRouter(tags=["management-analytics"])


def _parse_filters(raw: Optional[str]) -> dict:
    try:
        parsed = json.loads(raw) if raw else {}
        return parsed if isinstance(parsed, dict) else {}
    except (ValueError, TypeError):
        return {}


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
    record_filters: dict[str, list[str]] = {}
    date_sub_ranges: dict[str, dict] = {}


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
            record_filters=body.record_filters,
            date_sub_ranges=body.date_sub_ranges,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/analytics/dimensions")
def analytics_dimensions():
    return {
        "dimensions": dimensions_metadata(),
        "options": get_dimension_options(),
    }


@router.get("/analytics/metrics")
def analytics_metrics():
    """Unified metric catalog: every metric with subject, type and polarity."""
    return {"domains": METRIC_DOMAINS, "metrics": metrics_catalog()}


@router.get("/analytics/today")
def analytics_today(filters: str = Query("", description="JSON dimension filters")):
    return today_snapshot(_parse_filters(filters))


@router.get("/analytics/freshness")
def analytics_freshness(filters: str = Query("")):
    return freshness_snapshot(_parse_filters(filters))


@router.get("/analytics/signals")
def analytics_signals(
    start: str = Query(""),
    end: str = Query(""),
    filters: str = Query(""),
    limit: int = Query(12, ge=1, le=50),
):
    date_range = {"start": start, "end": end} if (start and end) else None
    return compute_signals(date_range, _parse_filters(filters), limit=limit)


@router.get("/analytics/forecast")
def analytics_forecast(
    filters: str = Query(""),
    window_weeks: int = Query(12, ge=4, le=52),
    horizon_weeks: int = Query(8, ge=1, le=26),
    outlook_weeks: int = Query(4, ge=1, le=12),
):
    return build_forecast(
        filters=_parse_filters(filters),
        window_weeks=window_weeks,
        horizon_weeks=horizon_weeks,
        outlook_weeks=outlook_weeks,
    )


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
