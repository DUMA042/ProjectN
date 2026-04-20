import pandas as pd
import sys

file_path = r'C:\Users\HP\Desktop\AttendanceN\nest\Training_Folder\Training_Sheet.xlsx'

def profile_sheet():
    try:
        # Check raw data to see where headers might be, similar to the nominal sheet
        df_raw = pd.read_excel(file_path, header=None)
        
        print("=== First 10 Raw Rows (to find headers) ===")
        print(df_raw.head(10).to_string())
        
        # Try to find a header row (often contains 'ID No' or something identifying)
        header_idx = 0
        for idx, row in df_raw.iterrows():
            # if we find common header-like strings. Let's look for "Name" or "ID"
            row_str = " ".join([str(c) for c in row if pd.notna(c)])
            if "Name" in row_str or "ID No" in row_str or "Course" in row_str:
                header_idx = idx
                break
                
        print(f"\nIdentified headers at row {header_idx}")
        df = pd.read_excel(file_path, header=header_idx)
        df.dropna(how='all', inplace=True)
        
        print("\n=== DataFrame Info ===")
        df.info()
        print("\n=== First 3 Rows ===")
        print(df.head(3).to_string())
        
        print("\n=== Unique Values Count (Cardinality) ===")
        print(df.nunique())
        
        print("\n=== Value Counts for Categorical Columns (Top 10) ===")
        for col in df.columns:
            if df[col].nunique() < 30 and col not in ['S/N', 'ID No.', 'Name']:
                print(f"\n--- {col} ---")
                print(df[col].value_counts().head(10))
                
    except Exception as e:
        print(f"Error profiling excel: {e}", file=sys.stderr)

if __name__ == '__main__':
    profile_sheet()
