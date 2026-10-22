"""Diagnostic: confirm the API can see its configuration. Never prints secrets."""
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from sqlalchemy.engine import make_url

from owl.config import settings, unknown_env_keys


def mask_url(url: str) -> str:
    """Return the URL with the password replaced by *** (safe to print)."""
    if not url:
        return "<not configured>"
    try:
        return make_url(url).render_as_string(hide_password=True)
    except Exception:  # noqa: BLE001 — never echo an unparsable value
        return "<configured, unparsable URL>"


def main() -> None:
    try:
        url = settings.get_database_url()
        print(f"Database URL: {mask_url(url)}")
    except Exception as exc:  # noqa: BLE001 — reported, not raised
        print(f"Database URL: <not configured> ({type(exc).__name__})")

    print(f"Environment:  {settings.environment}")
    print(f"Log level:    {settings.log_level} (effective: {settings.effective_log_level})")
    print(f"Data dir:     {settings.flow_data_dir}")
    print(f"API:          {settings.api_host}:{settings.api_port}")
    print(f"AI configured: {bool(settings.deepseek_api_key.strip())}")

    unknown = unknown_env_keys()
    if unknown:
        print("Unknown .env settings (ignored):")
        for key, suggestion in unknown:
            hint = f" — did you mean '{suggestion}'?" if suggestion else ""
            print(f"  - {key}{hint}")
    else:
        print("Unknown .env settings: none")


if __name__ == "__main__":
    main()
