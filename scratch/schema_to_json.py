import os
import json
from sqlalchemy import create_engine, inspect, text
from dotenv import load_dotenv

def dump_schema():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    engine = create_engine(db_url)
    inspector = inspect(engine)
    
    schema = {}
    tables = inspector.get_table_names()
    for table in tables:
        schema[table] = {
            "columns": [{"name": c["name"], "type": str(c["type"])} for c in inspector.get_columns(table)],
            "pk": inspector.get_pk_constraint(table).get('constrained_columns', []),
            "fks": inspector.get_foreign_keys(table)
        }
        
    with open('scratch/schema.json', 'w') as f:
        json.dump(schema, f, indent=2)

if __name__ == "__main__":
    dump_schema()
