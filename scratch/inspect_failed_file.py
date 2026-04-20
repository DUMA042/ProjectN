import pandas as pd
import openpyxl
from pathlib import Path

# Path to the quarantined file
file_path = Path(r"c:\Users\HP\Desktop\AttendanceN\nest\Quarantine\AttendanceSwipingCardReport202604101522022862764_1776046027.xlsx")

def inspect_file(path):
    print(f"Inspecting: {path.name}")
    # Read first 10 rows to see headers
    df = pd.read_excel(path, header=None, nrows=20)
    print("\nFirst 10 rows (header=None):")
    print(df.head(10))
    
    # Check sheets
    wb = openpyxl.load_workbook(path, read_only=True)
    print(f"\nSheets: {wb.sheetnames}")

if __name__ == "__main__":
    inspect_file(file_path)
