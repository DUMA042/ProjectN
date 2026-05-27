from datetime import date
import pandas as pd
import pytest

from owl.leave.processor import LeaveProcessor
from owl.load.models import LeaveApplication, LeaveRecord

# A dummy session to test what is being added
class DummySession:
    def __init__(self):
        self.added = []
    
    def add(self, obj):
        self.added.append(obj)
        
    def flush(self):
        # assign fake IDs for applications
        for obj in self.added:
            if isinstance(obj, LeaveApplication):
                obj.application_id = 999
                
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

@pytest.fixture
def processor():
    p = LeaveProcessor("dummy.xlsx")
    p.leave_types_dict = {
        "annual": 1,
        "maternity": 2,
        "sick": 3,
        "compassionate": 4,
        "paternity": 5,
        "pre-retirementleave": 6,
        "casualafterannual": 7,
        "exam": 8
    }
    p.valid_employees = {"EMP001"}
    return p

def test_parse_date_cell(processor):
    d, r = processor._parse_date_cell("01/05/2026")
    assert d == date(2026, 5, 1)
    assert r is None
    
    d, r = processor._parse_date_cell("PENDING")
    assert d is None
    assert r == "PENDING"
    
    d, r = processor._parse_date_cell(pd.NaT)
    assert d is None
    assert r is None

def test_process_row_latest_leave_mapping(processor):
    session = DummySession()
    
    # Create a dummy pandas Series matching the expected columns (at least 38 columns)
    row_data = [None] * 40
    row_data[2] = "EMP001" # STAFF ID
    row_data[6] = "01/01/2026" # PROPOSED LEAVE
    row_data[7] = "15/01/2026" # RESUMPTION
    
    # Let's add two leaves
    # Sick Leave (cols 29 & 30) - earlier
    row_data[29] = "10/02/2026"
    row_data[30] = "15/02/2026"
    
    # Compassionate Leave (cols 22 & 23) - later
    row_data[22] = "20/03/2026"
    row_data[23] = "25/03/2026"
    
    row = pd.Series(row_data)
    
    processor._process_row(1, row, session)
    
    # Should have 1 application and 2 records
    app = next(o for o in session.added if isinstance(o, LeaveApplication))
    assert app.proposed_leave_date == date(2026, 1, 1)
    
    records = [o for o in session.added if isinstance(o, LeaveRecord)]
    assert len(records) == 2
    
    sick_rec = next(r for r in records if r.leave_type_id == 3)
    compass_rec = next(r for r in records if r.leave_type_id == 4)
    
    # Sick is earlier, should NOT have planned dates mapped
    assert sick_rec.planned_start_date is None
    assert sick_rec.planned_end_date is None
    
    # Compassionate is later, should have planned dates mapped
    assert compass_rec.planned_start_date == date(2026, 1, 1)
    assert compass_rec.planned_end_date == date(2026, 1, 15)

def test_process_row_duration_calculation(processor):
    session = DummySession()
    
    row_data = [None] * 40
    row_data[2] = "EMP001"
    
    # cols 19 & 20 are Standalone Annual/Maternity
    # Let's make it <= 30 working days (e.g., 10 days) -> Annual Leave
    row_data[19] = "01/06/2026"
    row_data[20] = "10/06/2026"
    
    row = pd.Series(row_data)
    processor._process_row(1, row, session)
    
    records = [o for o in session.added if isinstance(o, LeaveRecord)]
    assert len(records) == 1
    assert records[0].leave_type_id == 1 # Annual Leave
    
    # Now try > 30 working days
    session = DummySession()
    row_data[19] = "01/01/2026"
    row_data[20] = "01/04/2026" # 3 months, ~60+ working days
    
    row = pd.Series(row_data)
    processor._process_row(2, row, session)
    
    records = [o for o in session.added if isinstance(o, LeaveRecord)]
    assert len(records) == 1
    assert records[0].leave_type_id == 2 # Maternity Leave
