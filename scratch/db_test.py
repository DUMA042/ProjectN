import psycopg2
import traceback

try:
    conn = psycopg2.connect(dbname='flowdb', user='postgres', password='1234', host='localhost', port='5433')
    cur = conn.cursor()
    
    print("TRIGGERS:")
    cur.execute("SELECT trigger_name, action_statement FROM information_schema.triggers WHERE event_object_table = 'file_ingestion_meta';")
    for row in cur.fetchall():
        print(row)
        
    print("\nAttempting raw insert:")
    cur.execute("""
        INSERT INTO file_ingestion_meta (
            original_filename, normalized_filename, file_path, checksum_sha256, status, error_context, version, file_size_bytes
        ) VALUES (
            'test.xlsx', 'test.xlsx', 'test.xlsx', 'N/A', 'quarantined', '{"reason": "test"}'::jsonb, 1, 0
        ) RETURNING period
    """)
    print("Insert result:", cur.fetchone())
    conn.rollback()
except Exception as e:
    traceback.print_exc()
