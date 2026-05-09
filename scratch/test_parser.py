import pandas as pd
import numpy as np

file_path = r'C:\Users\HP\Desktop\AttendanceN\tempFolder\Leave_testing_sheet.xlsx'

df = pd.read_excel(file_path, header=[0, 1])
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
    exit(1)
staff_id_idx = staff_id_indices[0]

# Clean staff id
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
                return s, e
        return None, None

    add_record('PRE-RETIREMENT LEAVE', "PRE- RETIREMENT LEAVE", "START DATE", "END DATE")
    add_record('ANNUAL LEAVE', "CASUAL BEFORE ANNUAL", "START DATE", "END DATE")
    
    # Casual After Annual first pair
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

print(f"Parsed {len(parsed_data)} applications.")
for app in parsed_data[:2]:
    print(app)
