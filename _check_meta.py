import sys; from pathlib import Path; sys.path.insert(0, str(Path.cwd()))
from sqlalchemy import text
from owl.load.database import get_session
with get_session() as s:
    types = s.execute(text("SELECT report_type, COUNT(*) FROM file_ingestion_meta GROUP BY report_type ORDER BY report_type")).fetchall()
    print("file_ingestion_meta report types:")
    for r in types: print(f"  {r[0]!r}: {r[1]}")
