import sys; from pathlib import Path; sys.path.insert(0, str(Path.cwd()))
from sqlalchemy import text
from owl.load.database import get_session
with get_session() as s:
    months = s.execute(text("SELECT EXTRACT(MONTH FROM swipe_time)::int AS m, COUNT(*) FROM employee_card_swipes GROUP BY m ORDER BY m")).fetchall()
    print("Swipes by month:")
    for r in months: print(f"  Month {r[0]}: {r[1]}")
    aug_q = s.execute(text("SELECT DISTINCT employee_name, COUNT(*) FROM quarantine_card_swipes WHERE swipe_time >= '2026-08-01' GROUP BY employee_name ORDER BY employee_name")).fetchall()
    print(f"Quarantined Aug names ({len(aug_q)}):")
    for r in aug_q: print(f"  {r[0]}: {r[1]}")
    sample_q = s.execute(text("SELECT employee_name, swipe_time FROM quarantine_card_swipes ORDER BY id DESC LIMIT 5")).fetchall()
    print("Latest quarantined:")
    for r in sample_q: print(f"  {r[0]} | {r[1]}")
