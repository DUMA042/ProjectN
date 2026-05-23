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
EXCEL_PATH = r"C:\Users\HP\Desktop\AttendanceN\nest\Nominal_Folder\Norminal_Sheet.xlsx"

def get_connection():
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
    return conn

def extract_and_transform():
    print("Reading Excel file...")
    # Read the sheet natively, skip 2 rows. Wait, if header=2 makes the real titles row 0...
    # Actually, the real headers are on row 3 in Excel (which is skip_rows=2, header=0, or just header=2).
    # But from profile output, it seems header=2 makes the true headers the *first data row*.
    # Let's read with header=3 just in case, or rather header=None and find the row with "ID No."
    df = pd.read_excel(EXCEL_PATH, header=None)
    
    # Find the row index that contains 'ID No.'
    header_idx = None
    for idx, row in df.iterrows():
        # check if 'ID No.' is in any cell in this row
        if any(str(cell).strip() == 'ID No.' for cell in row):
            header_idx = idx
            break
            
    if header_idx is None:
        print("CRITICAL ERROR: Could not find 'ID No.' header row in the file.")
        sys.exit(1)
        
    print(f"Found headers at row index {header_idx}")
    # Now set the columns to this row
    df.columns = [str(c).strip() for c in df.iloc[header_idx]]
    
    # Drop the header row and everything before it
    df = df.iloc[header_idx + 1:].reset_index(drop=True)
    
    # Drop completely empty rows and columns
    df.dropna(how='all', inplace=True)
    
    # Expected core columns
    expected_cols = {
        'ID No.': 'id_no', 
        'Name': 'full_name', 
        'Sex': 'sex', 
        'Department': 'department', 
        'Unit': 'unit', 
        'Location': 'location', 
        'GL': 'gl', 
        'Rank': 'rank', 
        'Employment Type': 'employment_type', 
        'Status': 'status', 
        'Remark': 'remark'
    }
    
    available_cols = {c: expected_cols[c] for c in expected_cols if c in df.columns}
    df = df[list(available_cols.keys())].copy()
    df.rename(columns=available_cols, inplace=True)
    
    if 'id_no' in df.columns:
        df.dropna(subset=['id_no'], inplace=True)
    else:
        print("CRITICAL ERROR: 'ID No.' column missing from Excel.")
        sys.exit(1)
        
    # Clean string data
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace({'nan': None, 'None': None, '': None})
        
    return df

def insert_lookups(cur, df):
    print("Populating Lookup Tables...")
    
    def insert_unique(table, col_name, df_col):
        if df_col not in df.columns: return
        unique_vals = [v for v in df[df_col].unique() if v is not None]
        for val in unique_vals:
            query = f"INSERT INTO {table} ({col_name}) VALUES (%s) ON CONFLICT ({col_name}) DO NOTHING"
            cur.execute(query, (val,))
            
    insert_unique('locations', 'location_name', 'location')
    insert_unique('departments', 'department_name', 'department')
    insert_unique('units', 'unit_name', 'unit')
    insert_unique('grade_levels', 'gl_name', 'gl')
    insert_unique('ranks', 'rank_name', 'rank')
    insert_unique('employment_types', 'emp_type_name', 'employment_type')
    insert_unique('employee_statuses', 'status_name', 'status')

def prepare_lookup_maps(cur):
    maps = {}
    queries = {
        'location': ('locations', 'location_name', 'location_id'),
        'department': ('departments', 'department_name', 'department_id'),
        'unit': ('units', 'unit_name', 'unit_id'),
        'gl': ('grade_levels', 'gl_name', 'gl_id'),
        'rank': ('ranks', 'rank_name', 'rank_id'),
        'emp_type': ('employment_types', 'emp_type_name', 'emp_type_id'),
        'status': ('employee_statuses', 'status_name', 'status_id')
    }
    for key, (table, name_col, id_col) in queries.items():
        cur.execute(f"SELECT {name_col}, {id_col} FROM {table}")
        maps[key] = {row[0]: row[1] for row in cur.fetchall()}
    return maps

def load_data(df):
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        insert_lookups(cur, df)
        maps = prepare_lookup_maps(cur)
        
        print("Migrating Employee Data...")
        count = 0
        for _, row in df.iterrows():
            id_no = row['id_no']
            
            u_id = maps['unit'].get(row.get('unit'))
            r_id = maps['rank'].get(row.get('rank'))
            e_id = maps['emp_type'].get(row.get('employment_type'))
            s_id = maps['status'].get(row.get('status'))
            
            # Use id_no string handling to be safe
            id_no_val = str(id_no).replace('.0', '')
            
            cur.execute("""
                INSERT INTO employees (id_no, full_name, sex, unit_id, rank_id, emp_type_id, status_id, remark)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id_no) DO NOTHING
            """, (id_no_val, row.get('full_name'), row.get('sex'), u_id, r_id, e_id, s_id, row.get('remark')))
            
            loc_id = maps['location'].get(row.get('location'))
            dept_id = maps['department'].get(row.get('department'))
            gl_id = maps['gl'].get(row.get('gl'))
            start_date = '2024-01-01'
            
            if loc_id is not None:
                cur.execute("SELECT 1 FROM employee_location_history WHERE id_no = %s AND end_date IS NULL", (id_no_val,))
                if not cur.fetchone():
                    cur.execute("INSERT INTO employee_location_history (id_no, location_id, start_date) VALUES (%s, %s, %s)", 
                                (id_no_val, loc_id, start_date))
                    
            if dept_id is not None:
                cur.execute("SELECT 1 FROM employee_department_history WHERE id_no = %s AND end_date IS NULL", (id_no_val,))
                if not cur.fetchone():
                    cur.execute("INSERT INTO employee_department_history (id_no, department_id, start_date) VALUES (%s, %s, %s)", 
                                (id_no_val, dept_id, start_date))
                    
            if gl_id is not None:
                cur.execute("SELECT 1 FROM employee_gl_history WHERE id_no = %s AND end_date IS NULL", (id_no_val,))
                if not cur.fetchone():
                    cur.execute("INSERT INTO employee_gl_history (id_no, gl_id, start_date) VALUES (%s, %s, %s)", 
                                (id_no_val, gl_id, start_date))
            
            count += 1
            if count % 200 == 0:
                print(f"Processed {count} records...")
                
        conn.commit()
        print(f"Migration Completed Successfully. Processed {count} total rows.")
        
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
