import sys; from pathlib import Path; sys.path.insert(0, str(Path.cwd()))
from sqlalchemy import text
from owl.load.database import get_session
with get_session() as s:
    recent = s.execute(text("SELECT normalized_filename, report_type, status, error_context, created_at FROM file_ingestion_meta ORDER BY created_at DESC LIMIT 3")).fetchall()
    print("Recent ingestions:")
    for r in recent:
        print(f"  {r[0]} | {r[1]} | {r[2]} | {str(r[3])[:100]} | {r[4]}")
    total = s.execute(text("SELECT COUNT(*), MAX(swipe_time) FROM employee_card_swipes")).fetchone()
    print(f"Total swipes: {total[0]}, Latest: {total[1]}")
    august = s.execute(text("SELECT swipe_time::date, COUNT(*) FROM employee_card_swipes WHERE swipe_time >= '2026-08-01' GROUP BY 1 ORDER BY 1")).fetchall()
    print("August swipes:")
    for r in august: print(f"  {r[0]}: {r[1]}")
