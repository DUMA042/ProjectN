# More detail on what IDs are rejected vs DB range
import json
import psycopg2

conn = psycopg2.connect('postgresql://postgres:1234@localhost:5433/flowdb')
cur = conn.cursor()

data = json.load(open('reports/leave_report_20260627_235139.json'))
invalid_ids = list({f['staff_id'] for f in data['failures'] if f['type'] == 'INVALID_STAFF_ID'})

cur.execute("SELECT id_no FROM employees")
all_db_ids = {r[0] for r in cur.fetchall()}

numeric_ids_in_file = sorted([int(i) for i in invalid_ids if i.strip().isdigit()])
db_nums = sorted([int(i) for i in all_db_ids if i.strip().isdigit()])

# IDs in file BELOW DB min (219)
below_min = [i for i in numeric_ids_in_file if i < 219]
print(f"IDs in file below DB minimum ({min(db_nums)}): {len(below_min)}")
print(f"Examples: {below_min[:20]}")

# IDs in file WITHIN DB range but not found
within_range = [i for i in numeric_ids_in_file if min(db_nums) <= i <= max(db_nums)]
print(f"\nIDs in file within DB range ({min(db_nums)}-{max(db_nums)}) but NOT in DB: {len(within_range)}")
print(f"Examples (these are genuinely missing employees): {within_range[:20]}")

# What does the file look like (read actual file)
cur.execute("SELECT file_path FROM file_ingestion_meta WHERE original_filename='2024Leave.xlsx'")
row = cur.fetchone()
if row:
    print(f"\nFile path in DB: {row[0]}")
