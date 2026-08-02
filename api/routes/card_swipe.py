"""Card Swipe analytics endpoints."""
from fastapi import APIRouter, Query
from ui.lib.queries import (
    get_card_swipe_summary,
    get_card_swipe_by_day,
    get_card_swipe_by_hour,
    get_card_swipe_by_month,
    get_card_swipe_by_location,
    get_recent_card_swipes,
)

router = APIRouter(tags=["card-swipe"])


@router.get("/card-swipe/summary")
def card_swipe_summary_api(today: bool = Query(False)):
    df = get_card_swipe_summary(today_only=today)
    return df.to_dict(orient="records")[0] if not df.empty else {}


@router.get("/card-swipe/by-day")
def card_swipe_by_day(days: int = Query(30, ge=1, le=365)):
    df = get_card_swipe_by_day(days)
    return df.to_dict(orient="records")


@router.get("/card-swipe/by-hour")
def card_swipe_by_hour():
    df = get_card_swipe_by_hour()
    return df.to_dict(orient="records")


@router.get("/card-swipe/by-month")
def card_swipe_by_month():
    df = get_card_swipe_by_month()
    return df.to_dict(orient="records")


@router.get("/card-swipe/by-location")
def card_swipe_by_location():
    df = get_card_swipe_by_location()
    return df.to_dict(orient="records")


@router.get("/card-swipe/recent")
def card_swipe_recent(limit: int = Query(50, ge=1, le=500)):
    df = get_recent_card_swipes(limit)
    return df.to_dict(orient="records")
