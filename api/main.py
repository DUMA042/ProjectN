"""FastAPI application entry point — AttendanceN API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from owl.config import settings

app = FastAPI(
    title="AttendanceN API",
    version="0.1.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins + ["http://localhost:1420"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from api.routes import health, analytics, ingestion, staff, kanban, card_swipe, leave_routes, training, dashboard_custom, settings_routes  # noqa: E402

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
