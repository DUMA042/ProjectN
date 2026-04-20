import pandas as pd
from pathlib import Path

file_path = Path(r"c:\Users\HP\Desktop\AttendanceN\inbox\AttendanceSwipingCardReport202604101522022862764.xlsx")

def check_headers(path):
    # Read the file to find where the headers are
    # This mimics the StructuralClassifier logic
    df_raw = pd.read_excel(path, header=None, nrows=10)
    print("Raw Data (First 5 rows):")
    print(df_raw.head(5))

if __name__ == "__main__":
    check_headers(file_path)
