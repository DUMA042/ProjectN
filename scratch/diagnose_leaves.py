import pandas as pd
from pathlib import Path
from owl.load.database import get_session
from owl.load.models import Employee, LeaveType
from sqlalchemy import select

def diagnose():
    # 1. Check DB Employees
    with get_session() as session:
        db_ids = session.execute(select(Employee.id_no)).scalars().all()
        print(f"Total Employees in DB: {len(db_ids)}")
        print(f"Sample IDs: {db_ids[:10]}")
        
        # 2. Check Leave Types
        lts = session.execute(select(LeaveType)).scalars().all()
        print("\nExisting Leave Types:")
        for lt in lts:
            print(f"  {lt.leave_type_id}: {lt.leave_type_name}")

    # 3. Check Excel file (if available in inbox)
    inbox = Path("inbox")
    files = list(inbox.glob("*.xlsx"))
    if files:
        file_path = files[0]
        print(f"\nAnalyzing Excel file: {file_path.name}")
        # We know the header is on row 1 (index 1) based on terminal output
        df = pd.read_excel(file_path, header=1)
        print(f"Total rows in Excel: {len(df)}")
        print(f"Excel Columns: {df.columns.tolist()}")
        
        staff_id_col = next((c for c in df.columns if "STAFF ID" in str(c).upper()), None)
        if staff_id_col:
            excel_ids = df[staff_id_col].astype(str).str.strip().unique().tolist()
            print(f"Unique Staff IDs in Excel: {len(excel_ids)}")
            print(f"Sample Excel IDs: {excel_ids[:10]}")
            
            matches = [id for id in excel_ids if id in db_ids]
            print(f"Matches found in DB: {len(matches)}")
            
            if len(matches) < 5:
                print("\nPOSSIBLE MISMATCH:")
                print(f"Example Excel ID: '{excel_ids[0]}' (Length: {len(excel_ids[0])})")
                if db_ids:
                    print(f"Example DB ID: '{db_ids[0]}' (Length: {len(db_ids[0])})")

if __name__ == "__main__":
    diagnose()
