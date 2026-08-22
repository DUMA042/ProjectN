import sys; from pathlib import Path; sys.path.insert(0, str(Path.cwd()))
from sqlalchemy import text
from owl.load.database import get_session
with get_session() as s:
    total = s.execute(text("SELECT COUNT(*) FROM leave_records")).fetchone()[0]
    nulls = s.execute(text("SELECT COUNT(*) FROM leave_records WHERE leave_type_id IS NULL")).fetchone()[0]
    print(f"Total leave_records: {total}")
    print(f"NULL leave_type_id: {nulls}")
    # Sample the NULL records
    samples = s.execute(text("SELECT record_id, id_no, start_date, end_date, planned_start_date, planned_end_date FROM leave_records WHERE leave_type_id IS NULL LIMIT 10")).fetchall()
    print("Sample NULL records:")
    for r in samples: print(f"  rec={r[0]} id={r[1]} start={r[2]} end={r[3]} planned_start={r[4]} planned_end={r[5]}")
    # Check leave_types
    types = s.execute(text("SELECT leave_type_id, leave_type_name FROM leave_types ORDER BY leave_type_id")).fetchall()
    print("Leave types:")
    for r in types: print(f"  {r[0]}: {r[1]}")
