import sys
from pathlib import Path

# Add project root to path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from owl.leave.processor import LeaveProcessor
from owl.load.database import get_session
from owl.load.models import LeaveType, Employee
import uuid

def setup_mock_data():
    """Ensure database has the required leave types and staff IDs for testing."""
    with get_session() as session:
        # Create missing leave types
        required = [
            "Pre-Retirement Leave",
            "Annual Leave",
            "Casual After Annual Leave",
            "Compassionate Leave",
            "Paternity Leave",
            "Maternity Leave",
            "Sick Leave",
            "Exam Leave",
        ]
        existing = {lt.leave_type_name for lt in session.query(LeaveType).all()}
        for req in required:
            if req not in existing:
                session.add(LeaveType(leave_type_name=req))
        
        # Create a mock employee (using the first staff ID found in test file if we know it,
        # but let's just create a few common ones or parse the file to find them).
        import pandas as pd
        df = pd.read_excel(_PROJECT_ROOT / "tempFolder" / "Leave test file 2026_19.xlsx", header=None)
        # Find the staff ids starting from row 2
        for i in range(2, len(df)):
            staff_id = str(df.iloc[i, 2]).strip()
            if staff_id and staff_id != 'nan':
                if not session.query(Employee).filter_by(id_no=staff_id).first():
                    emp = Employee(
                        id_no=staff_id,
                        full_name=f"Mock Employee {staff_id}",
                    )
                    session.add(emp)
        
        session.commit()

if __name__ == "__main__":
    setup_mock_data()
    file_path = _PROJECT_ROOT / "tempFolder" / "Leave test file 2026_19.xlsx"
    processor = LeaveProcessor(file_path=str(file_path))
    summary = processor.process()
    print("\n--- Processing Results ---")
    import json
    print(json.dumps(summary, indent=4))
