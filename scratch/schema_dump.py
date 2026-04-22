import os
from sqlalchemy import create_engine, inspect, text
from dotenv import load_dotenv

def dump_schema():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not found in .env")
        return

    engine = create_engine(db_url)
    inspector = inspect(engine)

    print("--- LIVE DATABASE SCHEMA DUMP ---")
    
    # 1. Tables
    tables = inspector.get_table_names()
    print(f"\nTables found ({len(tables)}):")
    for table in tables:
        print(f"  - {table}")
        
    # 2. Detailed Table Structure
    for table in tables:
        print(f"\nTABLE: {table}")
        
        # Columns
        print("  Columns:")
        columns = inspector.get_columns(table)
        for col in columns:
            nullable = "?" if col['nullable'] else "NOT NULL"
            default = f" DEFAULT {col['default']}" if col.get('default') else ""
            print(f"    - {col['name']}: {col['type']} {nullable}{default}")
            
        # PK
        pk = inspector.get_pk_constraint(table)
        print(f"  Primary Key: {pk['constrained_columns']}")
        
        # FK
        fks = inspector.get_foreign_keys(table)
        if fks:
            print("  Foreign Keys:")
            for fk in fks:
                print(f"    - {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")
                
        # Indexes
        indexes = inspector.get_indexes(table)
        if indexes:
            print("  Indexes:")
            for idx in indexes:
                cols = ", ".join(idx['column_names'])
                unique = "UNIQUE " if idx['unique'] else ""
                print(f"    - {idx['name']} ({cols}) {unique}")

    # 3. Rules (Postgres specific)
    print("\n--- Postgres Rules ---")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT tablename, rulename, definition FROM pg_rules WHERE schemaname = 'public';"))
        rules = result.all()
        if rules:
            for rule in rules:
                print(f"Table: {rule[0]}, Rule: {rule[1]}")
                print(f"Definition: {rule[2]}\n")
        else:
            print("No rules found.")

if __name__ == "__main__":
    dump_schema()
