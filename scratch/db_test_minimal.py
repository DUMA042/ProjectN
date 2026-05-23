import psycopg2
import traceback

try:
    conn = psycopg2.connect(dbname='flowdb', user='postgres', password='1234', host='localhost', port='5433')
    cur = conn.cursor()
    
    print("\nAttempting raw insert minimal:")
    cur.execute("""
        INSERT INTO file_ingestion_meta (
            original_filename, normalized_filename, file_path, checksum_sha256, status
        ) VALUES (
            'test.xlsx', 'test.xlsx', 'test.xlsx', 'N/A', 'quarantined'
        ) 
    """)
    print("Insert result success")
    conn.rollback()
except Exception as e:
    traceback.print_exc()
