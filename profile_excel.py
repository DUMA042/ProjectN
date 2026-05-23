import pandas as pd
import sys

file_path = r'C:\Users\HP\Desktop\AttendanceN\nest\Nominal_Folder\Norminal_Sheet.xlsx'

try:
    # Read with header=2 because the first two rows are titles/blank
    df = pd.read_excel(file_path, header=2)
    # The columns to ignore:
    cols_to_ignore = ['Date of Last Deployment', 'Residential Address', 'Residential State']
    df = df.drop(columns=[col for col in cols_to_ignore if col in df.columns], errors='ignore')
    
    print("=== DataFrame Info ===")
    df.info()
    print("\n=== First 3 Rows ===")
    print(df.head(3).to_string())
    print("\n=== Unique Values Count (Cardinality) ===")
    print(df.nunique())
    print("\n=== Value Counts for Categorical Columns ===")
    categorical_cols = ['Sex', 'GL', 'Rank', 'Department', 'Unit', 'Location', 'Employment Type', 'Status', 'Remark']
    for col in categorical_cols:
        if col in df.columns:
            print(f"\n--- {col} ---")
            print(df[col].value_counts().head(10)) # Top 10 to keep it brief
            print(f"Total Unique: {df[col].nunique()}")
            
except Exception as e:
    print(f"Error reading excel: {e}", file=sys.stderr)
