"""Health check endpoint."""

from fastapi import APIRouter, Depends

from owl.load.database import verify_connection

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    verify_connection()
    return {"status": "ok", "db": "connected"}
