"""
owl.config
~~~~~~~~~~
Centralised, type-safe settings loaded from the environment / .env file.

Usage
-----
    from owl.config import settings

    engine = create_engine(settings.database_url)
"""

from __future__ import annotations

import difflib
import os
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _expand_path(value: Path | str) -> Path:
    """Expand %VARS% / $VARS and ~ — so FLOW_DATA_DIR=%APPDATA%\\Flow works."""
    return Path(os.path.expandvars(str(value))).expanduser()


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

    # ── Pipeline / data location ──────────────────────────────────────────────
    # One root for every generated artifact. In development the default is the
    # project folder (unchanged behaviour). A packaged desktop install sets
    # FLOW_DATA_DIR=%APPDATA%\Flow so files never land in a read-only
    # Program Files directory.
    flow_data_dir: Path = Field(
        default=Path("."),
        description="Root directory for uploads, reports, and other app data.",
    )

    nest_dir: Optional[Path] = Field(
        default=None,
        description="Directory containing raw Excel source files "
                    "(default: <flow_data_dir>/nest).",
    )

    inbox_dir: Optional[Path] = Field(
        default=None,
        description="Landing zone for new file uploads "
                    "(default: <flow_data_dir>/inbox).",
    )

    report_inbox_dir: Optional[Path] = Field(
        default=None,
        description="Sent-to-Report-Builder file store, sensitive — never commit "
                    "(default: <flow_data_dir>/report_inbox).",
    )

    @model_validator(mode="after")
    def _derive_data_paths(self) -> "Settings":
        """Fill unset artifact paths from flow_data_dir (explicit values win)."""
        base = _expand_path(self.flow_data_dir).resolve()
        self.flow_data_dir = base
        if self.nest_dir is None:
            self.nest_dir = base / "nest"
        if self.inbox_dir is None:
            self.inbox_dir = base / "inbox"
        if self.report_inbox_dir is None:
            self.report_inbox_dir = base / "report_inbox"
        return self

    max_file_size_mb: int = Field(
        default=50,
        description="Files larger than this (MB) will be read in streaming mode to avoid memory exhaustion.",
    )

    max_upload_mb: int = Field(
        default=200,
        description="Hard limit for uploads (MB). Larger files are rejected outright.",
    )

    # ── API ────────────────────────────────────────────────────────────────────
    api_host: str = Field(
        default="127.0.0.1",
        description="Host address for the FastAPI server.",
    )

    api_port: int = Field(
        default=8001,
        description="Port for the FastAPI server (single source of truth).",
    )

    cors_origins: list[str] = Field(
        default=["http://localhost:1420"],
        description="Allowed CORS origins for the frontend (Tauri dev port).",
    )

    # ── AI (DeepSeek) ─────────────────────────────────────────────────────────
    # Empty default = unconfigured (fail-closed). The key lives ONLY in the
    # operator's local .env — it is never logged, never sent to the frontend,
    # and never returned by any endpoint.
    deepseek_api_key: str = Field(
        default="",
        description="DeepSeek API key (sk-...). Leave empty to disable AI features.",
    )
    deepseek_model: str = Field(
        default="deepseek-flash",
        description="DeepSeek model for assistant replies (flash, not pro).",
    )

    reader_database_url: str = Field(
        default="",
        description=(
            "Optional separate connection string for the read-only chatbot role. "
            "When empty, the executor uses the app session inside a read-only "
            "transaction instead. Example: postgresql+psycopg2://flow_reader:PASSWORD@localhost:5432/owl_db"
        ),
    )

    max_concurrent_ai_calls: int = Field(
        default=2,
        description="Maximum simultaneous outbound AI requests for this process.",
    )

    def get_deepseek_key(self) -> str:
        """Return the DeepSeek key, or raise if AI is not configured."""
        if not self.deepseek_api_key.strip():
            raise ValueError(
                "DEEPSEEK_API_KEY is not configured. "
                "Add it to your local .env (never commit it) and restart the API."
            )
        return self.deepseek_api_key.strip()

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

    # ── Derived runtime helpers (pure, testable) ─────────────────────────────
    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def effective_log_level(self) -> str:
        """Production defaults to WARNING; development keeps the chosen level."""
        if not self.is_development and self.log_level == "INFO":
            return "WARNING"
        return self.log_level

    @property
    def docs_enabled(self) -> bool:
        """Interactive API docs are a development convenience only."""
        return self.is_development


def unknown_env_keys(env_file: Path | str = ".env") -> list[tuple[str, str | None]]:
    """Return (key, suggested_key) for .env entries that match no setting.

    Only the .env *file* is inspected — the operating-system environment is
    intentionally left permissive (Windows defines hundreds of variables).
    A typo like MAX_FILESIZE_MB would otherwise be discarded silently and the
    real setting would keep its default.
    """
    path = Path(env_file)
    if not path.exists():
        return []
    known = {name.lower(): name.upper() for name in Settings.model_fields}
    found: list[tuple[str, str | None]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        key = line.split("=", 1)[0].strip()
        if not key:
            continue
        normalised = key.lower()
        if normalised in known:
            continue
        close = difflib.get_close_matches(normalised, known.keys(), n=1, cutoff=0.75)
        found.append((key, known[close[0]] if close else None))
    return found


# Singleton — import this object everywhere; do NOT instantiate Settings yourself.
settings = Settings()
