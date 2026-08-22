import sys; from pathlib import Path; sys.path.insert(0, str(Path.cwd()))
from sqlalchemy import text
from owl.load.database import get_session
with get_session() as s:
    seqs = s.execute(text("SELECT sequence_name FROM information_schema.sequences WHERE sequence_name LIKE '%leave%'")).fetchall()
    print('Sequences:', [r[0] for r in seqs])
    lr = s.execute(text("SELECT COUNT(*) FROM leave_records")).scalar()
    la = s.execute(text("SELECT COUNT(*) FROM leave_applications")).scalar()
    meta = s.execute(text("SELECT COUNT(*) FROM file_ingestion_meta WHERE report_type = 'Leave'")).scalar()
    print(f"leave_records={lr}, leave_applications={la}, leave meta={meta}")
