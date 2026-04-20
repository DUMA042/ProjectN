import os
import sys

from pathlib import Path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

try:
    from owl.config import settings
    url = settings.get_database_url()
    print(f"URL from settings: {url}")
except Exception as e:
    print(f"Exception: {e}")

print("Env var:", os.environ.get("DATABASE_URL"))
