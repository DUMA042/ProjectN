"""
owl.config
~~~~~~~~~~
Centralised, type-safe settings loaded from the environment / .env file.

Usage
-----
    from owl.config import settings

    engine = create_engine(settings.database_url)
"""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide configuration.

    All values can be overridden via environment variables or a `.env` file
    located at the project root.  Variable names are case-insensitive.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────────
    # Uses a sentinel default so the package is importable without a .env file.
    # Call settings.get_database_url() at runtime — it raises clearly if unset.
    database_url: str = Field(
        default="",
        description=(
            "SQLAlchemy connection string. "
            "Example: postgresql+psycopg2://user:pass@localhost:5432/owl_db"
        ),
    )

    def get_database_url(self) -> str:
        """Return validated database URL, or raise if not configured."""
        if not self.database_url:
            raise ValueError(
                "DATABASE_URL is not configured. "
                "Copy .env.example → .env and set DATABASE_URL."
            )
        return self.database_url

    # ── Pipeline ──────────────────────────────────────────────────────────────
    nest_dir: Path = Field(
        default=Path("nest"),
        description="Directory containing raw Excel source files.",
    )

    inbox_dir: Path = Field(
        default=Path("inbox"),
        description="Landing zone for new file uploads.",
    )

    max_file_size_mb: int = Field(
        default=50,
        description="Files larger than this (MB) will be read in streaming mode to avoid memory exhaustion.",
    )

    # ── API ────────────────────────────────────────────────────────────────────
    api_host: str = Field(
        default="127.0.0.1",
        description="Host address for the FastAPI server.",
    )

    api_port: int = Field(
        default=8000,
        description="Port for the FastAPI server.",
    )

    cors_origins: list[str] = Field(
        default=["http://localhost:1420"],
        description="Allowed CORS origins for the frontend (Tauri dev port).",
    )

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: str = Field(
        default="INFO",
        description="Logging verbosity. One of DEBUG | INFO | WARNING | ERROR | CRITICAL.",
    )

    # ── Runtime ───────────────────────────────────────────────────────────────
    environment: str = Field(
        default="development",
        description="Runtime environment. One of development | staging | production.",
    )

    # ── Validators ────────────────────────────────────────────────────────────
    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = value.upper()
        if upper not in allowed:
            raise ValueError(f"log_level must be one of {allowed}, got '{value}'")
        return upper

    @field_validator("environment")
    @classmethod
    def _validate_environment(cls, value: str) -> str:
        allowed = {"development", "staging", "production"}
        lower = value.lower()
        if lower not in allowed:
            raise ValueError(f"environment must be one of {allowed}, got '{value}'")
        return lower


# Singleton — import this object everywhere; do NOT instantiate Settings yourself.
settings = Settings()
