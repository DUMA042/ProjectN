"""FastAPI application entry point — AttendanceN API."""

from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from owl.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup sweep + shutdown hooks."""
    _sweep_stuck_jobs()
    yield


def _sweep_stuck_jobs() -> None:
    """Mark long-stuck 'processing' records as failed on server startup.

    If the server died mid-processing, rows would otherwise remain in
    'processing' forever and never be retried.
    """
    try:
        from sqlalchemy import select

        from owl.load.database import get_session
        from owl.load.models import FileIngestionMeta

        cutoff = datetime.now() - timedelta(minutes=30)
        with get_session() as session:
            stale = session.execute(
                select(FileIngestionMeta).where(
                    FileIngestionMeta.status == "processing",
                    FileIngestionMeta.created_at < cutoff,
                )
            ).scalars().all()
            for record in stale:
                record.status = "failed"
                record.processed_at = datetime.now()
                record.error_context = {
                    "fatal_error": "Server restarted mid-processing — job recovered as failed."
                }
            session.commit()

        if stale:
            import logging
            logging.getLogger("owl.startup").warning(
                f"Startup sweep: marked {len(stale)} stuck 'processing' job(s) as failed."
            )
    except Exception:  # noqa: BLE001 — startup must never crash because of the sweep
        import logging
        logging.getLogger("owl.startup").exception("Startup stuck-job sweep failed.")


app = FastAPI(
    title="AttendanceN API",
    version="0.1.0",
    docs_url="/docs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins + ["http://localhost:1420"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from api.routes import health, analytics, ingestion, staff, kanban, card_swipe, leave_routes, training, dashboard_custom, settings_routes, rules, quarantine  # noqa: E402

app.include_router(health.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(ingestion.router, prefix="/api")
app.include_router(staff.router, prefix="/api")
app.include_router(kanban.router, prefix="/api")
app.include_router(card_swipe.router, prefix="/api")
app.include_router(leave_routes.router, prefix="/api")
app.include_router(training.router, prefix="/api")
app.include_router(dashboard_custom.router, prefix="/api")
app.include_router(settings_routes.router, prefix="/api")
app.include_router(rules.router, prefix="/api")
app.include_router(quarantine.router, prefix="/api")
