import sys; from pathlib import Path; sys.path.insert(0, str(Path.cwd()))
from sqlalchemy import text
from owl.load.database import get_session
with get_session() as s:
    # Check if there are any records in the range of file dates
    for d in ['2026-08-03','2026-08-04','2026-08-05','2026-08-06','2026-08-07']:
        c = s.execute(text(f"SELECT COUNT(*) FROM employee_card_swipes WHERE swipe_time::date = :d"), {"d": d}).fetchone()
        print(f"{d}: {c[0]} in main table")
    # Check raw timestamp of latest 3 records
    latest = s.execute(text("SELECT swipe_id, id_no, swipe_time, swipe_time::date FROM employee_card_swipes ORDER BY swipe_id DESC LIMIT 3")).fetchall()
    print("Latest 3 by swipe_id:")
    for r in latest: print(f"  id={r[0]} id_no={r[1]} raw={r[2]} date={r[3]}")
    # Check if ANY date contains '08' as month
    has_aug = s.execute(text("SELECT COUNT(*) FROM employee_card_swipes WHERE DATE_PART('month', swipe_time) = 8")).fetchone()
    print(f"Month 8 count: {has_aug[0]}")
    # Check total count diff
    total = s.execute(text("SELECT COUNT(*) FROM employee_card_swipes")).fetchone()
    print(f"Total: {total[0]}")
