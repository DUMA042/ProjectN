import sys; from pathlib import Path; sys.path.insert(0, str(Path.cwd()))
from sqlalchemy import text
from owl.load.database import get_session
with get_session() as s:
    v3 = s.execute(text("SELECT error_context FROM file_ingestion_meta WHERE normalized_filename = 'AHRD_CardSwipe_202608_v3.xlsx'")).fetchone()
    ctx = v3[0] if v3 else {}
    import json
    if isinstance(ctx, dict):
        lr = ctx.get("load_results", {})
        print(f"load_results: {json.dumps(lr, indent=2, default=str)}")
        vr = ctx.get("validation_results", {})
        print(f"validation: rejected={vr.get('total_rejected', 0)}")
    else:
        print(f"ctx: {ctx}")
