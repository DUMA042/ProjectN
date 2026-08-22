import sys, json; from pathlib import Path; sys.path.insert(0, str(Path.cwd()))
from sqlalchemy import text
from owl.load.database import get_session
with get_session() as s:
    v7 = s.execute(text("SELECT error_context FROM file_ingestion_meta WHERE normalized_filename = 'AHRD_CardSwipe_202608_v7.xlsx'")).fetchone()
    ctx = v7[0] if v7 else {}
    if isinstance(ctx, dict):
        print(f"status: {ctx.get('status')}")
        lr = ctx.get("load_results", {})
        print(f"load_results: {json.dumps(lr, default=str, indent=2)}")
        vr = ctx.get("validation_results", {})
        print(f"validation_rejected: {vr.get('total_rejected', 0)}")
    aug = s.execute(text("SELECT swipe_time::date, COUNT(*) FROM employee_card_swipes WHERE swipe_time >= '2026-08-01' GROUP BY 1 ORDER BY 1")).fetchall()
    print(f"August: {len(aug)} days")
