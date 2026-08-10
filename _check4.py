import sys; from pathlib import Path; sys.path.insert(0, str(Path.cwd()))
from sqlalchemy import text
from owl.load.database import get_session
with get_session() as s:
    total = s.execute(text("SELECT COUNT(*), MIN(swipe_time::date), MAX(swipe_time::date) FROM employee_card_swipes")).fetchone()
    print(f"Total: {total[0]}, Range: {total[1]} to {total[2]}")
    aug = s.execute(text("SELECT swipe_time::date, COUNT(*) FROM employee_card_swipes WHERE swipe_time >= '2026-08-01'::timestamptz GROUP BY 1 ORDER BY 1 LIMIT 10")).fetchall()
    print("August:")
    for r in aug: print(f"  {r[0]}: {r[1]}")
    if not aug:
        sample = s.execute(text("SELECT id_no, swipe_time FROM employee_card_swipes ORDER BY swipe_time DESC LIMIT 3")).fetchall()
        print("Latest 3 swipes:")
        for r in sample: print(f"  {r[0]}: {r[1]}")
