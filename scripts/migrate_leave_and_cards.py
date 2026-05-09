import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys
import re
import os
import glob

# Connection Settings
DB_NAME = "flowdb"
DB_USER = "postgres"
DB_PASSWORD = "1234"
DB_HOST = "localhost"
DB_PORT = "5433"

LEAVE_FOLDER = r'C:\Users\HP\Desktop\AttendanceN\nest\Leave_Folder'
CARD_FOLDER = r'C:\Users\HP\Desktop\AttendanceN\nest\Card_Swiping_Folder'

def get_connection():
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
    return conn

def extract_leave_data():
    print("Reading Leave file...")
    
    files = glob.glob(os.path.join(LEAVE_FOLDER, '*.xlsx'))
    if not files:
        print("CRITICAL ERROR: No Excel file found in Leave_Folder.")
        sys.exit(1)
        
    leave_file = files[0]
    print(f"Processing: {leave_file}")
    
    df = pd.read_excel(leave_file, header=[0, 1])
    cols = []
    for col in df.columns:
        c0 = str(col[0]).strip().upper() if "Unnamed" not in str(col[0]) else ""
        c1 = str(col[1]).strip().upper() if "Unnamed" not in str(col[1]) else ""
        cols.append((c0, c1))

    def get_col_indices(level0, level1=""):
        indices = []
        for i, c in enumerate(cols):
            if level0 in c[0] and level1 in c[1]:
                indices.append(i)
        return indices

    staff_id_indices = get_col_indices("", "STAFF ID")
    if not staff_id_indices:
        print("CRITICAL ERROR: 'STAFF ID' column missing.")
        sys.exit(1)
    staff_id_idx = staff_id_indices[0]

    df.dropna(subset=[df.columns[staff_id_idx]], inplace=True)

    parsed_data = []

    for _, row in df.iterrows():
        staff_id = str(row.iloc[staff_id_idx]).replace('.0', '').strip()
        if staff_id == 'nan' or staff_id == 'NAN' or not staff_id: continue
        
        def get_val(l0, l1, idx=0):
            indices = get_col_indices(l0, l1)
            if len(indices) > idx:
                val = row.iloc[indices[idx]]
                return val if pd.notna(val) else ""
            return ""
            
        app = {
            'id_no': staff_id,
            'proposed_leave_date_raw': str(get_val("", "PROPOSED LEAVE DATE")),
            'resumption_date': pd.to_datetime(get_val("", "RESUMPTION DATE"), errors='coerce'),
            'forfeiture': str(get_val("CASUAL AFTER ANNUAL", "FORFEITURE")),
            'issuance_date_raw': str(get_val("SUMMARY", "ISSUANCE DATE")),
            'remark': str(get_val("STAFF FILE", "REMARK")),
            'records': []
        }
        
        app['proposed_leave_date'] = pd.to_datetime(app['proposed_leave_date_raw'], errors='coerce')
        app['issuance_date'] = pd.to_datetime(app['issuance_date_raw'], errors='coerce')
        
        def add_record(leave_type, l0, start_l1, end_l1, start_idx=0, end_idx=0):
            s_indices = get_col_indices(l0, start_l1)
            e_indices = get_col_indices(l0, end_l1)
            if len(s_indices) > start_idx and len(e_indices) > end_idx:
                s_val = row.iloc[s_indices[start_idx]]
                e_val = row.iloc[e_indices[end_idx]]
                s = pd.to_datetime(s_val, errors='coerce')
                e = pd.to_datetime(e_val, errors='coerce')
                if pd.notna(s):
                    app['records'].append({'type': leave_type, 'start': s, 'end': e})

        add_record('PRE-RETIREMENT LEAVE', "PRE- RETIREMENT LEAVE", "START DATE", "END DATE")
        add_record('ANNUAL LEAVE', "CASUAL BEFORE ANNUAL", "START DATE", "END DATE")
        add_record('CASUAL AFTER ANNUAL', "CASUAL AFTER ANNUAL", "START DATE", "END DATE", start_idx=0, end_idx=0)
        
        # Casual After Annual second pair (Special rule)
        s_indices = get_col_indices("CASUAL AFTER ANNUAL", "START DATE")
        e_indices = get_col_indices("CASUAL AFTER ANNUAL", "END DATE.1")
        if len(s_indices) > 1 and len(e_indices) > 0:
            s_val = row.iloc[s_indices[1]]
            e_val = row.iloc[e_indices[0]]
            s = pd.to_datetime(s_val, errors='coerce')
            e = pd.to_datetime(e_val, errors='coerce')
            
            if pd.notna(s) and pd.notna(e):
                days = np.busday_count(s.date(), e.date())
                ltype = 'MATERNITY LEAVE' if days > 30 else 'ANNUAL LEAVE'
                app['records'].append({'type': ltype, 'start': s, 'end': e})
            elif pd.notna(s):
                 app['records'].append({'type': 'ANNUAL LEAVE', 'start': s, 'end': e})

        add_record('COMPASSIONATE LEAVE', "COMPASSIONATE LEAVE", "START DATE", "END DATE")
        add_record('PATERNITY LEAVE', "PATERNITY LEAVE", "START DATE", "END DATE")
        add_record('SICK LEAVE', "SICK LEAVE", "START DATE", "END DATE")
        add_record('EXAM LEAVE', "EXAM LEAVE", "START DATE", "END DATE")

        parsed_data.append(app)

    return parsed_data

def extract_card_data():
    print("Reading Card file...")
    files = glob.glob(os.path.join(CARD_FOLDER, '*.xlsx'))
    if not files:
        print("No Card Swiping file found. Skipping card data.")
        return None
        
    card_file = files[0]
    print(f"Processing: {card_file}")
    
    # Find headers
    df_raw = pd.read_excel(card_file, header=None, nrows=20)
    header_idx = None
    for idx, row in df_raw.iterrows():
        row_str = " ".join([str(c) for c in row if pd.notna(c)]).lower()
        if "name" in row_str and "time" in row_str:
            header_idx = idx
            break
            
    if header_idx is None:
        print("CRITICAL ERROR: Could not find header row in the Card file.")
        sys.exit(1)
        
    df = pd.read_excel(card_file, header=header_idx)
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
            std_name = str(name).strip().upper()
            name_map[std_name] = id_no
    return name_map

def load_leave_data(cur, parsed_applications):
    print("Loading Leave Data...")
    
    cur.execute("SELECT leave_type_name, leave_type_id FROM leave_types")
    type_map = {row[0]: row[1] for row in cur.fetchall()}
    
    app_count = 0
    skipped_count = 0
    record_count = 0
    
    for app in parsed_applications:
        id_no = app['id_no']
        cur.execute("SELECT 1 FROM employees WHERE id_no = %s", (id_no,))
        if not cur.fetchone():
            skipped_count += 1
            continue
            
        # Overwrite logic: DELETE existing applications for this ID (cascade deletes records)
        cur.execute("DELETE FROM leave_applications WHERE id_no = %s", (id_no,))
        
        # Insert application metadata
        p_date = app['proposed_leave_date'].date() if pd.notna(app['proposed_leave_date']) else None
        r_date = app['resumption_date'].date() if pd.notna(app['resumption_date']) else None
        i_date = app['issuance_date'].date() if pd.notna(app['issuance_date']) else None
        
        cur.execute("""
            INSERT INTO leave_applications 
            (id_no, proposed_leave_date, proposed_leave_date_raw, resumption_date, 
             forfeiture, issuance_date, issuance_date_raw, remark)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING application_id
        """, (id_no, p_date, app['proposed_leave_date_raw'], r_date, 
              app['forfeiture'], i_date, app['issuance_date_raw'], app['remark']))
              
        app_id = cur.fetchone()[0]
        app_count += 1
        
        # Insert records
        for rec in app['records']:
            t_id = type_map.get(rec['type'])
            if not t_id: continue
            
            s_date = rec['start'].date() if pd.notna(rec['start']) else None
            e_date = rec['end'].date() if pd.notna(rec['end']) else None
            
            cur.execute("""
                INSERT INTO leave_records (application_id, id_no, leave_type_id, start_date, end_date)
                VALUES (%s, %s, %s, %s, %s)
            """, (app_id, id_no, t_id, s_date, e_date))
            record_count += 1
            
    print(f"Loaded {app_count} valid Leave Applications with {record_count} specific leave records. Skipped {skipped_count} where ID wasn't found.")

def load_card_data(cur, df_card):
    print("Loading Card Swiping Data... This may take a minute...")
    name_map = create_name_to_id_map(cur)
    
    cur.execute("INSERT INTO locations (location_name) VALUES ('HQ') ON CONFLICT (location_name) DO NOTHING")
    cur.execute("SELECT location_id FROM locations WHERE location_name = 'HQ'")
    loc_id = cur.fetchone()
    loc_id = loc_id[0] if loc_id else None
    
    swipe_count = 0
    orphan_count = 0
    
    for _, row in df_card.iterrows():
        name = row['name']
        s_time = row['swipe_time']
        
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
    parsed_leave = extract_leave_data()
    df_card = extract_card_data()
    
    conn = get_connection()
    cur = conn.cursor()
    try:
        load_leave_data(cur, parsed_leave)
        if df_card is not None:
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
