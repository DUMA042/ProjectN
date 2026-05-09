import pandas as pd
import json

file_path = r'C:\Users\HP\Desktop\AttendanceN\tempFolder\Leave_testing_sheet.xlsx'

df_multi = pd.read_excel(file_path, header=[0, 1], nrows=5)
cols = []
for col in df_multi.columns:
    cols.append(list(col))

with open(r'C:\Users\HP\Desktop\AttendanceN\scratch\cols.json', 'w') as f:
    json.dump(cols, f, indent=2)
