"""Training analytics endpoints."""
from fastapi import APIRouter, Query
from ui.lib.queries import (
    get_training_summary,
    get_training_by_venue,
    get_training_by_consultant,
    get_recent_trainings,
)

router = APIRouter(tags=["training"])


@router.get("/training/summary")
def training_summary():
    df = get_training_summary()
    return df.to_dict(orient="records")[0] if not df.empty else {}


@router.get("/training/by-venue")
def training_by_venue():
    df = get_training_by_venue()
    return df.to_dict(orient="records")


@router.get("/training/by-consultant")
def training_by_consultant():
    df = get_training_by_consultant()
    return df.to_dict(orient="records")


@router.get("/training/recent")
def training_recent(limit: int = Query(50, ge=1, le=500)):
    df = get_recent_trainings(limit)
    return df.to_dict(orient="records")
