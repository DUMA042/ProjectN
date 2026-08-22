import sys; from pathlib import Path; sys.path.insert(0, str(Path.cwd()))
from sqlalchemy import text
from owl.load.database import get_session
with get_session() as s:
    before = s.execute(text("SELECT COUNT(*) FROM employee_card_swipes")).fetchone()[0]
    misdated = s.execute(text("SELECT COUNT(*) FROM employee_card_swipes WHERE EXTRACT(DAY FROM swipe_time)=8 AND EXTRACT(MONTH FROM swipe_time) IN (3,4,5,6,7)")).fetchone()[0]
    print(f"Misdated records (day=8, month 3-7): {misdated} of {before}")
    s.execute(text("DELETE FROM employee_card_swipes WHERE EXTRACT(DAY FROM swipe_time)=8 AND EXTRACT(MONTH FROM swipe_time) IN (3,4,5,6,7)"))
    s.execute(text("DELETE FROM quarantine_card_swipes WHERE swipe_time >= '2026-08-01'"))
    s.execute(text("DELETE FROM file_ingestion_meta WHERE normalized_filename IN ('AHRD_CardSwipe_202608_v4.xlsx','AHRD_CardSwipe_202608_v5.xlsx','AHRD_CardSwipe_202608_v6.xlsx','AHRD_CardSwipe_202608_v7.xlsx')"))
    s.commit()
    after = s.execute(text("SELECT COUNT(*) FROM employee_card_swipes")).fetchone()[0]
    print(f"Cleaned. Remaining: {after} (removed {before - after})")
    months = s.execute(text("SELECT EXTRACT(MONTH FROM swipe_time)::int, COUNT(*) FROM employee_card_swipes GROUP BY 1 ORDER BY 1")).fetchall()
    print("By month:", {r[0]: r[1] for r in months})
