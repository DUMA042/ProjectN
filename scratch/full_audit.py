import hashlib
from pathlib import Path
from owl.load.database import get_session
from sqlalchemy import select
from owl.load.models import FileIngestionMeta

def get_sha(p):
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except:
        return "ERROR"

print("--- FILE SYSTEM AUDIT ---")
nest_folder = Path(r"c:\Users\HP\Desktop\AttendanceN\nest\card_Swiping_Folder")
quarantine_folder = Path(r"c:\Users\HP\Desktop\AttendanceN\nest\Quarantine")

print(f"\nFolder: {nest_folder}")
for f in nest_folder.glob("*.xlsx"):
    print(f"  {f.name:40} | Size: {f.stat().st_size:10} | SHA: {get_sha(f)}")

print(f"\nFolder: {quarantine_folder}")
for f in quarantine_folder.glob("AttendanceSwiping*"):
    print(f"  {f.name:40} | Size: {f.stat().st_size:10} | SHA: {get_sha(f)}")

print("\n--- DATABASE AUDIT ---")
with get_session() as session:
    jobs = session.execute(select(FileIngestionMeta).order_by(FileIngestionMeta.id)).scalars().all()
    for j in jobs:
        if "CardSwipe" in str(j.report_type) or "AttendanceSwiping" in j.original_filename:
             print(f"  ID: {str(j.id)[:8]}... | Orig: {j.original_filename:30} | Status: {j.status:12} | DB_SHA: {j.checksum_sha256}")
