import pandas as pd
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys

# Connection Settings
DB_NAME = "flowdb"
DB_USER = "postgres"
DB_PASSWORD = "1234"
DB_HOST = "localhost"
DB_PORT = "5433"
EXCEL_PATH = r"C:\Users\HP\Desktop\AttendanceN\nest\Training_Folder\Training_Sheet.xlsx"

def get_connection():
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
    return conn

def extract_and_transform():
    print("Reading Training Excel file...")
    # Based on our previous profiling, header is effectively at index 0 
    # but we search dynamically to be safe
    df = pd.read_excel(EXCEL_PATH, header=None)
    
    header_idx = None
    for idx, row in df.iterrows():
        row_str = " ".join([str(c) for c in row if pd.notna(c)])
        if "Venue" in row_str or "Consultant" in row_str:
            header_idx = idx
            break
            
    if header_idx is None:
        print("CRITICAL ERROR: Could not find header row in the Training file.")
        sys.exit(1)
        
    print(f"Found headers at row {header_idx}")
    df.columns = [str(c).strip() for c in df.iloc[header_idx]]
    df = df.iloc[header_idx + 1:].reset_index(drop=True)
    df.dropna(how='all', inplace=True)
    
    # Expected columns from the sheet
    expected_cols = {
        'id': 'id_no', 
        'Venue': 'venue', 
        'Consultant': 'consultant', 
        'Start Date': 'start_date', 
        'End Date': 'end_date', 
        'Location': 'location'
    }
    
    available_cols = {c: expected_cols[c] for c in expected_cols if c in df.columns}
    df = df[list(available_cols.keys())].copy()
    df.rename(columns=available_cols, inplace=True)
    
    if 'id_no' in df.columns:
        df.dropna(subset=['id_no'], inplace=True)
    else:
        print("CRITICAL ERROR: 'id' column missing from English.")
        sys.exit(1)
        
    # Clean string data
    for col in ['id_no', 'venue', 'consultant', 'location']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace({'nan': None, 'None': None, '': None})
            
    # Dates should be proper datetimes, we ensure they are parsed
    df['start_date'] = pd.to_datetime(df['start_date'], errors='coerce')
    df['end_date'] = pd.to_datetime(df['end_date'], errors='coerce')
    
    # Drop rows without valid dates or valid employee ids
    df.dropna(subset=['start_date', 'end_date'], inplace=True)
    
    return df

def insert_lookups(cur, df):
    print("Populating Lookup Tables for Training Data...")
    
    def insert_unique(table, col_name, df_col):
        if df_col not in df.columns: return
        unique_vals = [v for v in df[df_col].unique() if v is not None]
        for val in unique_vals:
            query = f"INSERT INTO {table} ({col_name}) VALUES (%s) ON CONFLICT ({col_name}) DO NOTHING"
            cur.execute(query, (val,))
            
    insert_unique('venues', 'venue_name', 'venue')
    insert_unique('consultants', 'consultant_name', 'consultant')
    insert_unique('locations', 'location_name', 'location')  # Some locations might be new to this sheet

def prepare_lookup_maps(cur):
    maps = {}
    queries = {
        'venue': ('venues', 'venue_name', 'venue_id'),
        'consultant': ('consultants', 'consultant_name', 'consultant_id'),
        'location': ('locations', 'location_name', 'location_id')
    }
    for key, (table, name_col, id_col) in queries.items():
        cur.execute(f"SELECT {name_col}, {id_col} FROM {table}")
        maps[key] = {row[0]: row[1] for row in cur.fetchall()}
    return maps

def load_data(df):
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Load any new dims
        insert_lookups(cur, df)
        maps = prepare_lookup_maps(cur)
        
        print("Migrating Training Data Records...")
        count = 0
        skipped = 0
        
        for _, row in df.iterrows():
            # Standardize ID string (similar to main ETL)
            id_no_val = str(row['id_no']).replace('.0', '')
            
            # Verify the employee actually exists in `employees` table
            cur.execute("SELECT 1 FROM employees WHERE id_no = %s", (id_no_val,))
            if not cur.fetchone():
                print(f"Warning: Employee ID '{id_no_val}' not found in DB. Skipping training record.")
                skipped += 1
                continue
            
            v_id = maps['venue'].get(row.get('venue'))
            c_id = maps['consultant'].get(row.get('consultant'))
            l_id = maps['location'].get(row.get('location'))
            s_date = row.get('start_date').date() if pd.notna(row.get('start_date')) else min_date
            e_date = row.get('end_date').date() if pd.notna(row.get('end_date')) else min_date
            
            cur.execute("""
                INSERT INTO employee_trainings (id_no, venue_id, consultant_id, location_id, start_date, end_date)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (id_no_val, v_id, c_id, l_id, s_date, e_date))
            
            count += 1
            
        conn.commit()
        print(f"Migration Completed Successfully. Processed {count} records, skipped {skipped} unmapped employees.")
        
    except Exception as e:
        conn.rollback()
        print(f"Migration Failed: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    df = extract_and_transform()
    load_data(df)
