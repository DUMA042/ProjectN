import pandas as pd
import numpy as np

file_path = r'C:\Users\HP\Desktop\AttendanceN\tempFolder\Leave_testing_sheet.xlsx'

# Read the first few rows to inspect headers
df = pd.read_excel(file_path, header=None, nrows=20)
print("=== First 10 rows of raw data ===")
print(df.head(10).to_string())

# Also read it with header=[0, 1] to see if it's a multiindex
df_multi = pd.read_excel(file_path, header=[0, 1], nrows=5)
print("\n=== MultiIndex Columns ===")
for col in df_multi.columns:
    print(col)
