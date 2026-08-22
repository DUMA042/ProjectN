import sys; from pathlib import Path; sys.path.insert(0, str(Path.cwd()))
from sqlalchemy import text
from owl.load.database import get_session
with get_session() as s:
    rows = s.execute(text("""
        SELECT record_id, id_no, start_date, end_date,
               planned_start_date, planned_end_date,
               start_date_raw, end_date_raw
        FROM leave_records
        WHERE leave_type_id IS NULL
          AND start_date IS NOT NULL
          AND end_date IS NOT NULL
          AND end_date > '1950-01-01'
        ORDER BY record_id
        LIMIT 30
    """)).fetchall()
    print(f"NULL-type records with real dates (first 30):")
    for r in rows:
        print(f"  rec={r[0]} id={r[1]} start={r[2]} end={r[3]} planned={r[4]}->{r[5]} raw_start={r[6]!r} raw_end={r[7]!r}")
    total = s.execute(text("""
        SELECT COUNT(*) FROM leave_records
        WHERE leave_type_id IS NULL AND start_date IS NOT NULL AND end_date IS NOT NULL AND end_date > '1950-01-01'
    """)).fetchone()[0]
    print(f"\nTotal NULL-type with real dates: {total}")
