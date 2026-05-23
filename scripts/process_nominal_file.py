import sys
from pathlib import Path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from datetime import datetime
from sqlalchemy import select, update
from owl.load.database import get_session
from owl.load.models import FileIngestionMeta
from owl.nominal.processor import NominalProcessor
from owl.logger import get_logger
import hashlib

log = get_logger(__name__)

def get_checksum(file_path: Path) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def process_nominal(file_path: Path):
    with get_session() as session:
        # Check if already processed
        stmt = select(FileIngestionMeta).where(FileIngestionMeta.original_filename == file_path.name)
        existing = session.execute(stmt).scalars().first()
        
        if existing and existing.status == "completed":
            log.info(f"File {file_path.name} is already processed.")
            return

        log.info(f"File {file_path.name} not processed. Creating metadata record...")
        if not existing:
            meta = FileIngestionMeta(
                original_filename=file_path.name,
                normalized_filename=file_path.name,
                file_path=str(file_path),
                checksum_sha256=get_checksum(file_path),
                file_size_bytes=file_path.stat().st_size,
                report_type="nominal_roll",
                status="processing",
                department="HR"
            )
            session.add(meta)
            session.flush()
            meta_id = meta.id
            session.commit()
        else:
            existing.status = "processing"
            session.commit()
            meta_id = existing.id

    log.info(f"Running NominalProcessor on {file_path}...")
    processor = NominalProcessor(file_path)
    summary = processor.process()

    with get_session() as session:
        stmt = (
            update(FileIngestionMeta)
            .where(FileIngestionMeta.id == meta_id)
            .values(
                status="completed",
                processed_at=datetime.now(),
                error_context={"load_results": summary}
            )
        )
        session.execute(stmt)
        session.commit()
    log.info(f"Successfully processed and updated FileIngestionMeta for {file_path.name}")

if __name__ == "__main__":
    file_path = Path("nest/Nominal_Folder/AHRD_Nominal_202605_v1.xlsx")
    if file_path.exists():
        try:
            process_nominal(file_path)
        except Exception as e:
            import traceback
            print("ERROR OCCURRED:", repr(e))
            if hasattr(e, "__cause__") and e.__cause__:
                print("CAUSE:", repr(e.__cause__))
            with open("fatal_error.txt", "w", encoding="utf-8") as f:
                traceback.print_exc(file=f)
    else:
        log.error(f"File not found: {file_path}")
