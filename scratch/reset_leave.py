import psycopg2
import sys
conn = psycopg2.connect('postgresql://postgres:1234@localhost:5433/flowdb')
cur = conn.cursor()
cur.execute("UPDATE file_ingestion_meta SET status='pending' WHERE original_filename='2025Leave.xlsx'")
conn.commit()
print("Updated!")
