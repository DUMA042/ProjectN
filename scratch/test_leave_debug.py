import sys
import traceback
from owl.leave.processor import LeaveProcessor

try:
    processor = LeaveProcessor(r'nest\Quarantine\2025Leave_1782595959.xlsx')
    processor.process()
    print("Success")
except Exception as e:
    print("Failed with exception:")
    traceback.print_exc()
