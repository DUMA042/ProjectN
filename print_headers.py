import sys
from pathlib import Path
from owl.extract.excel_reader import ExcelReader

def check_headers():
    file_path = Path("nest/Nominal_Folder/AHRD_Nominal_202604_v2.xlsx")
    reader = ExcelReader(file_path=file_path, header_row=0)
    frames = reader.read()
    for sheet, df in frames.items():
        print(f"Sheet: {sheet}")
        print(f"Headers: {df.columns.tolist()}")

if __name__ == "__main__":
    check_headers()
