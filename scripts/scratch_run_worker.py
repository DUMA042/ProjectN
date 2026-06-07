import sys
from pathlib import Path
_PROJECT_ROOT = Path("c:/Users/HP/Desktop/AttendanceN").resolve()
sys.path.insert(0, str(_PROJECT_ROOT))
from owl.load.database import get_session
from owl.load.models import FileIngestionMeta
from owl.ingest.worker import IngestionWorker

with get_session() as session:
    meta = session.query(FileIngestionMeta).filter(FileIngestionMeta.original_filename == "Training2507.xlsx").first()
    if meta:
        meta.status = "pending"
        session.commit()

worker = IngestionWorker()
worker.run_once()
