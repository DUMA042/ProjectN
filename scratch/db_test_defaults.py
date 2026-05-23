import psycopg2
import traceback

try:
    conn = psycopg2.connect(dbname='flowdb', user='postgres', password='1234', host='localhost', port='5433')
    cur = conn.cursor()
    cur.execute("""
        SELECT a.attname, pg_get_expr(d.adbin, d.adrelid)
        FROM pg_attribute a
        LEFT JOIN pg_attrdef d ON a.attrelid = d.adrelid AND a.attnum = d.adnum
        WHERE a.attrelid = 'file_ingestion_meta'::regclass AND a.attnum > 0 AND NOT a.attisdropped;
    """)
    print('Defaults:', cur.fetchall())
except Exception as e:
    traceback.print_exc()
