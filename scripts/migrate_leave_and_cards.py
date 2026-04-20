import pandas as pd
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys
import re

# Connection Settings
DB_NAME = "flowdb"
DB_USER = "postgres"
DB_PASSWORD = "1234"
DB_HOST = "localhost"
DB_PORT = "5433"

LEAVE_FILE = r'C:\Users\HP\Desktop\AttendanceN\nest\Leave_Folder\Leave sheet Feb 1st to 14th.xlsx'
CARD_FILE = r'C:\Users\HP\Desktop\AttendanceN\nest\Card_Swiping_Folder\AttendanceSwipingCardReport2wkfeb2026.xlsx'

def get_connection():
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
    return conn

def extract_leave_data():
    print("Reading Leave file...")
    # Find headers dynamically
    df_raw = pd.read_excel(LEAVE_FILE, header=None)
    header_idx = None
    for idx, row in df_raw.iterrows():
        row_str = " ".join([str(c) for c in row if pd.notna(c)]).lower()
        if "leave" in row_str and "staff" in row_str:
            header_idx = idx
            break
            
    if header_idx is None:
        print("CRITICAL ERROR: Could not find header row in the Leave file.")
        sys.exit(1)
        
    df = pd.read_excel(LEAVE_FILE, header=header_idx)
    df.dropna(how='all', inplace=True)
    
    # Expected columns for leave
    expected_cols = {
        'STAFF ID': 'id_no', 
        'START DATE': 'start_date', 
        'END DATE': 'end_date', 
        'LEAVE TYPE': 'leave_type'
    }
    
    available_cols = {c: expected_cols[c] for c in expected_cols if c in df.columns}
    df = df[list(available_cols.keys())].copy()
    df.rename(columns=available_cols, inplace=True)
    
    if 'id_no' in df.columns:
        df.dropna(subset=['id_no'], inplace=True)
        df['id_no'] = df['id_no'].astype(str).str.replace('.0', '', regex=False).str.strip()
    else:
        print("CRITICAL ERROR: 'STAFF ID' column missing from Leave Sheet.")
        sys.exit(1)
        
    df['start_date'] = pd.to_datetime(df['start_date'], errors='coerce')
    df['end_date'] = pd.to_datetime(df['end_date'], errors='coerce')
    df.dropna(subset=['start_date'], inplace=True) # start_date must exist
    
    df['leave_type'] = df['leave_type'].astype(str).str.strip().str.upper()
    
    return df

def extract_card_data():
    print("Reading Card file...")
    # Find headers
    df_raw = pd.read_excel(CARD_FILE, header=None, nrows=20)
    header_idx = None
    for idx, row in df_raw.iterrows():
        row_str = " ".join([str(c) for c in row if pd.notna(c)]).lower()
        if "name" in row_str and "time" in row_str:
            header_idx = idx
            break
            
    if header_idx is None:
        print("CRITICAL ERROR: Could not find header row in the Card file.")
        sys.exit(1)
        
    df = pd.read_excel(CARD_FILE, header=header_idx)
    df.dropna(how='all', inplace=True)
    
    # Expected columns for Card
    expected_cols = {
        'Name': 'name', 
        'Card Swiping Time': 'swipe_time', 
        'Location': 'location'
    }
    
    available_cols = {c: expected_cols[c] for c in expected_cols if c in df.columns}
    df = df[list(available_cols.keys())].copy()
    df.rename(columns=available_cols, inplace=True)
    
    if 'name' not in df.columns or 'swipe_time' not in df.columns:
        print("CRITICAL ERROR: Required columns missing from Card Sheet.")
        sys.exit(1)
        
    df.dropna(subset=['name', 'swipe_time'], inplace=True)
    df['name'] = df['name'].astype(str).str.strip().str.upper()
    df['swipe_time'] = pd.to_datetime(df['swipe_time'], errors='coerce')
    df.dropna(subset=['swipe_time'], inplace=True)
    
    return df

def create_name_to_id_map(cur):
    """Creates a dictionary mapping standardized employee names to their ID"""
    cur.execute("SELECT id_no, full_name FROM employees")
    rows = cur.fetchall()
    
    name_map = {}
    for id_no, name in rows:
        if name:
            # simple standardization 
            std_name = str(name).strip().upper()
            name_map[std_name] = id_no
    return name_map

def load_leave_data(cur, df_leave):
    print("Loading Leave Data...")
    
    # Insert leave types
    unique_types = [v for v in df_leave['leave_type'].unique() if pd.notna(v) and v != "NAN"]
    for t in unique_types:
        cur.execute("INSERT INTO leave_types (leave_type_name) VALUES (%s) ON CONFLICT (leave_type_name) DO NOTHING", (t,))
        
    cur.execute("SELECT leave_type_name, leave_type_id FROM leave_types")
    type_map = {row[0]: row[1] for row in cur.fetchall()}
    
    leave_count = 0
    skipped_leave_count = 0
    for _, row in df_leave.iterrows():
        id_no = row['id_no']
        cur.execute("SELECT 1 FROM employees WHERE id_no = %s", (id_no,))
        if not cur.fetchone():
            skipped_leave_count += 1
            continue
            
        t_id = type_map.get(row['leave_type'])
        if not t_id:
            continue
            
        s_date = row['start_date'].date() if pd.notna(row['start_date']) else None
        e_date = row['end_date'].date() if pd.notna(row['end_date']) else None
        
        cur.execute("""
            INSERT INTO employee_leaves (id_no, leave_type_id, start_date, end_date)
            VALUES (%s, %s, %s, %s)
        """, (id_no, t_id, s_date, e_date))
        leave_count += 1
        
    print(f"Loaded {leave_count} Leave valid records. Skipped {skipped_leave_count} where ID wasn't found.")

def load_card_data(cur, df_card):
    print("Loading Card Swiping Data... This may take a minute...")
    name_map = create_name_to_id_map(cur)
    
    # HQ location assumes existing, standard insertion
    cur.execute("INSERT INTO locations (location_name) VALUES ('HQ') ON CONFLICT (location_name) DO NOTHING")
    cur.execute("SELECT location_id FROM locations WHERE location_name = 'HQ'")
    loc_id = cur.fetchone()
    loc_id = loc_id[0] if loc_id else None
    
    swipe_count = 0
    orphan_count = 0
    
    for _, row in df_card.iterrows():
        name = row['name']
        s_time = row['swipe_time']
        
        # Get ID via exact string match (standardized slightly)
        id_no = name_map.get(name)
        if not id_no:
            orphan_count += 1
            continue
            
        cur.execute("""
            INSERT INTO employee_card_swipes (id_no, location_id, swipe_time)
            VALUES (%s, %s, %s)
        """, (id_no, loc_id, s_time))
        
        swipe_count += 1
        if swipe_count % 5000 == 0:
            print(f"  ...processed {swipe_count} swipes...")
            
    print(f"Loaded {swipe_count} Card Swipes. Skipped {orphan_count} records due to unmapped names.")

def migrate():
    df_leave = extract_leave_data()
    df_card = extract_card_data()
    
    conn = get_connection()
    cur = conn.cursor()
    try:
        load_leave_data(cur, df_leave)
        load_card_data(cur, df_card)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Migration Failed: {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()
        
    print("Complete!")

if __name__ == "__main__":
    migrate()
