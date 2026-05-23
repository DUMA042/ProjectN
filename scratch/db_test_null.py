import psycopg2
import traceback
from sqlalchemy import null
from owl.load.database import get_session
from owl.load.models import FileIngestionMeta

try:
    with get_session() as session:
        ingestion = FileIngestionMeta(
            original_filename='Leave file 2026.xlsx',
            normalized_filename='Leave file 2026.xlsx',
            file_path='nest/Quarantine/test.xlsx',
            checksum_sha256='N/A',
            status='quarantined',
            error_context={'reason': 'test'},
            version=1,
            file_size_bytes=0,
            period=null()
        )
        session.add(ingestion)
        session.commit()
    print('Success with null()!')
except Exception as e:
    traceback.print_exc()
