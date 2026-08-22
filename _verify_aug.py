import sys; from pathlib import Path; sys.path.insert(0, str(Path.cwd()))
from sqlalchemy import text
from owl.load.database import get_session
with get_session() as s:
    # Check August data in employee_card_swipes
    aug = s.execute(text("SELECT swipe_time::date, COUNT(*) FROM employee_card_swipes WHERE swipe_time >= '2026-08-01' GROUP BY 1 ORDER BY 1")).fetchall()
    print("August swipes:")
    for r in aug: print(f"  {r[0]}: {r[1]}")
    if not aug:
        print("  NONE - no August data in DB yet")
    # Check quarantine for August
    q = s.execute(text("SELECT employee_name, COUNT(*) FROM quarantine_card_swipes WHERE swipe_time >= '2026-08-01' GROUP BY employee_name ORDER BY employee_name")).fetchall()
    print(f"Quarantined Aug ({len(q)} names):")
    for r in q: print(f"  {r[0]}: {r[1]}")
    # Check recent ingestions
    recent = s.execute(text("SELECT normalized_filename, report_type, status, created_at FROM file_ingestion_meta ORDER BY created_at DESC LIMIT 3")).fetchall()
    print("Recent ingestions:")
    for r in recent: print(f"  {r[0]} | {r[1]} | {r[2]} | {r[3]}")
