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
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from api.routes import health, analytics, ingestion, staff, kanban  # noqa: E402

app.include_router(health.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(ingestion.router, prefix="/api")
app.include_router(staff.router, prefix="/api")
app.include_router(kanban.router, prefix="/api")
