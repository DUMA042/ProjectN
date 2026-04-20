import pandas as pd
import sys

file_leave = r'C:\Users\HP\Desktop\AttendanceN\nest\Leave_Folder\Leave sheet Feb 1st to 14th.xlsx'
file_card = r'C:\Users\HP\Desktop\AttendanceN\nest\Card_Swiping_Folder\AttendanceSwipingCardReport2wkfeb2026.xlsx'

def profile_sheet(file_path, name):
    print(f"\n======================================")
    print(f"PROFILING: {name}")
    print(f"======================================")
    try:
        # Check raw data to see where headers might be, similar to the nominal sheet
        df_raw = pd.read_excel(file_path, header=None)
        
        print("\n=== First 10 Raw Rows (to find headers) ===")
        print(df_raw.head(10).to_string())
        
        # Try to find a header row
        header_idx = 0
        for idx, row in df_raw.iterrows():
            row_str = " ".join([str(c) for c in row if pd.notna(c)]).lower()
            if "name" in row_str or "id" in row_str or "date" in row_str or "leave" in row_str:
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
            # Print value counts for columns that seem categorical, or just to get an idea
            if df[col].nunique() < 30 and 'id' not in str(col).lower() and 'name' not in str(col).lower():
                print(f"\n--- {col} ---")
                print(df[col].value_counts(dropna=False).head(10))
                
    except Exception as e:
        print(f"Error profiling {name}: {e}", file=sys.stderr)

if __name__ == '__main__':
    profile_sheet(file_leave, "LEAVE SHEET")
    profile_sheet(file_card, "SWIPING CARD SHEET")
