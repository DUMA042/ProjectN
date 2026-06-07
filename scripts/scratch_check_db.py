import sys
from pathlib import Path

_PROJECT_ROOT = Path("c:/Users/HP/Desktop/AttendanceN").resolve()
sys.path.insert(0, str(_PROJECT_ROOT))

from owl.load.database import get_session
from owl.load.models import FileIngestionMeta

with open("db_output.txt", "w") as f:
    with get_session() as session:
        results = session.query(FileIngestionMeta).order_by(FileIngestionMeta.created_at.desc()).limit(3).all()
        for r in results:
            f.write(f"Name: {r.original_filename}\n")
            f.write(f"Status: {r.status}\n")
            f.write(f"Error Context: {r.error_context}\n")
            f.write("-" * 40 + "\n")
