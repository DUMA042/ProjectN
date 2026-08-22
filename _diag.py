import sys; from pathlib import Path; sys.path.insert(0, str(Path.cwd()))
from sqlalchemy import text
from owl.load.database import get_session
with get_session() as s:
    latest = s.execute(text("SELECT normalized_filename, report_type, status, error_context, created_at FROM file_ingestion_meta ORDER BY created_at DESC LIMIT 3")).fetchall()
    print("Latest 3 ingestions:")
    for r in latest:
        ctx = str(r[3])[:300] if r[3] else "None"
        print(f"  {r[0]} | {r[1]} | {r[2]} | {ctx[:150]}")
        print()
    total = s.execute(text("SELECT COUNT(*), MAX(swipe_time) FROM employee_card_swipes")).fetchone()
    print(f"Swipes: {total[0]}, Latest: {total[1]}")
    q_total = s.execute(text("SELECT COUNT(*) FROM quarantine_card_swipes")).fetchone()
    print(f"Quarantine: {q_total[0]}")
