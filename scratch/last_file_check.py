import psycopg2
import json

conn = psycopg2.connect('postgresql://postgres:1234@localhost:5433/flowdb')
cur = conn.cursor()

# Get last 5 files ordered by detected_at (creation time) not updated_at
cur.execute("""
    SELECT original_filename, normalized_filename, status, error_context, 
           file_path, detected_at, processed_at
    FROM file_ingestion_meta 
    ORDER BY detected_at DESC LIMIT 5
""")
rows = cur.fetchall()
cols = ['filename', 'normalized', 'status', 'error_context', 'file_path', 'detected_at', 'processed_at']
for row in rows:
    print(json.dumps(dict(zip(cols, [str(v) for v in row])), indent=2))
    print("---")
