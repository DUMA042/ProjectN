import psycopg2
import sys
import traceback
from owl.leave.processor import LeaveProcessor

conn = psycopg2.connect('postgresql://postgres:1234@localhost:5433/flowdb')
cur = conn.cursor()
cur.execute("SELECT file_path FROM file_ingestion_meta WHERE original_filename='2024Leave.xlsx'")
res = cur.fetchone()
if not res:
    print("File not found in DB")
    sys.exit(1)

file_path = res[0]
print(f"Testing file path: {file_path}")

try:
    processor = LeaveProcessor(file_path)
    processor.process()
    print("Success")
except Exception as e:
    print("Failed with exception:")
    traceback.print_exc()
