import psycopg2
import traceback

try:
    conn = psycopg2.connect(dbname='flowdb', user='postgres', password='1234', host='localhost', port='5433')
    cur = conn.cursor()
    cur.execute("SELECT * FROM pg_rules WHERE tablename = 'file_ingestion_meta';")
    print('Rules:', cur.fetchall())
except Exception as e:
    traceback.print_exc()
