import psycopg2
import json
from dotenv import load_dotenv
import os

load_dotenv()
conn = psycopg2.connect(dbname='flowdb', user='postgres', password='1234', host='localhost', port='5433')
cur = conn.cursor()

print("--- RECENT INGESTION ERRORS ---")
cur.execute("SELECT original_filename, status, error_context FROM file_ingestion_meta ORDER BY created_at DESC LIMIT 5;")
for row in cur.fetchall():
    print(f"File: {row[0]} | Status: {row[1]}")
    if row[2]:
        print(f"Errors: {json.dumps(row[2], indent=2)[:500]}...")

print("\n--- SCHEMA EXPORT ---")
cur.execute("""
SELECT t.table_name, c.column_name, c.data_type
FROM information_schema.tables t
JOIN information_schema.columns c ON t.table_name = c.table_name
WHERE t.table_schema = 'public'
ORDER BY t.table_name, c.ordinal_position;
""")
with open("schema_dump.md", "w") as f:
    f.write("# FlowDB Schema\n\n")
    current_table = None
    for row in cur.fetchall():
        table, col, dtype = row
        if table != current_table:
            f.write(f"\n### `{table}`\n")
            f.write("| Column | Type |\n|---|---|\n")
            current_table = table
        f.write(f"| {col} | {dtype} |\n")

print("Schema written to schema_dump.md")
