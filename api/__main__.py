"""Entry point for the packaged API sidecar (``flow-api.exe``).

The desktop manager sets ``FLOW_BOOTSTRAP=1`` on first and every launch, so
this process applies Alembic migrations and (when a seed bundle is present)
loads the employee roster before serving HTTP.

All bootstrap output goes to stderr, which the manager captures in
``logs/api.log``.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _bundle_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent.parent


def _log(message: str) -> None:
    print(f"[bootstrap] {message}", file=sys.stderr, flush=True)


def apply_migrations(root: Path) -> None:
    from alembic import command
    from alembic.config import Config

    from owl.config import settings

    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    config.set_main_option("sqlalchemy.url", settings.get_database_url())
    command.upgrade(config, "head")
    _log("migrations applied")


def apply_seed(root: Path) -> None:
    from scripts.load_seed import seed_if_empty

    seed_dir = Path(os.environ.get("FLOW_SEED_DIR") or (root / "seed"))
    if not seed_dir.is_dir():
        _log(f"no seed bundle at {seed_dir}; starting with an empty roster")
        return

    result = seed_if_empty(seed_dir)
    if result.get("skipped"):
        _log(f"seed skipped: {result.get('reason')}")
    else:
        _log(f"seed applied: {result.get('seeded')}")


def main() -> None:
    root = _bundle_root()

    if os.environ.get("FLOW_BOOTSTRAP") == "1":
        apply_migrations(root)
        apply_seed(root)

    import uvicorn

    from owl.config import settings

    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
