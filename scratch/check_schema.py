from owl.load.database import get_engine
from sqlalchemy import text

conn = get_engine().connect()
result = conn.execute(text("SELECT column_name, is_generated, generation_expression FROM information_schema.columns WHERE table_name = 'file_ingestion_meta' AND column_name = 'period'")).fetchall()
print("Postgres DB period column:")
print(result)

result_all = conn.execute(text("SELECT column_name, is_generated, generation_expression FROM information_schema.columns WHERE table_name = 'file_ingestion_meta'")).fetchall()
print("\nAll columns with is_generated:")
for r in result_all:
    if r[1] != 'NEVER':
        print(r)
