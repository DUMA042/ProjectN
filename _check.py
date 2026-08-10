import sys; from pathlib import Path; sys.path.insert(0, str(Path.cwd()))
from sqlalchemy import text
from owl.load.database import get_session
with get_session() as s:
    swipes = s.execute(text("SELECT COUNT(*), MIN(swipe_time), MAX(swipe_time) FROM employee_card_swipes WHERE swipe_time::date BETWEEN '2026-08-03' AND '2026-08-08'")).fetchone()
    print(f"employee_card_swipes Aug 3-8: {swipes[0]} records")
    quarantine = s.execute(text("SELECT COUNT(*) FROM quarantine_card_swipes WHERE swipe_time::date BETWEEN '2026-08-03' AND '2026-08-08'")).fetchone()
    print(f"quarantine_card_swipes Aug 3-8: {quarantine[0]} records")
    recent = s.execute(text("SELECT normalized_filename, report_type, status FROM file_ingestion_meta ORDER BY created_at DESC LIMIT 3")).fetchall()
    print("Recent ingestions:")
    for r in recent: print(f"  {r[0]} | {r[1]} | {r[2]}")
