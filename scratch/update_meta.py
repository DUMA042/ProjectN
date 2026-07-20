import psycopg2

conn = psycopg2.connect('postgresql://postgres:1234@localhost:5433/flowdb')
cur = conn.cursor()

# Update the DB record to reflect that it has been manually quarantined
cur.execute("""
    UPDATE file_ingestion_meta
    SET status = 'quarantined',
        file_path = 'nest\\Quarantine\\2024Leave_MISCLASSIFIED.xlsx',
        error_context = '{"reason": "Misclassified as Nominal Roll — Leave file with 2024 header structure. Manually moved to quarantine."}'::jsonb
    WHERE original_filename = '2024Leave.xlsx'
""")
conn.commit()
print(f"Rows updated: {cur.rowcount}")
conn.close()
