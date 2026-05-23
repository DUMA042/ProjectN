import sys
from pathlib import Path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
from owl.load.database import get_session
from sqlalchemy import text

with get_session() as session:
    res = session.execute(text("SELECT tgname FROM pg_trigger WHERE tgrelid = 'employees'::regclass")).fetchall()
    print("Triggers:", res)
    for row in res:
        trigger_name = row[0]
        if not trigger_name.startswith("RI_ConstraintTrigger"):
            print(f"Dropping {trigger_name}")
            session.execute(text(f"DROP TRIGGER IF EXISTS {trigger_name} ON employees"))
    session.commit()
    print("Done")
