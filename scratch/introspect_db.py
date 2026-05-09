import os
from sqlalchemy import inspect, create_engine, text
from dotenv import load_dotenv

def generate_ddl():
    load_dotenv()
    db_url = os.getenv('DATABASE_URL')
    engine = create_engine(db_url)
    inspector = inspect(engine)
    
    output = []
    output.append("-- ==========================================")
    output.append("-- DATABASE SCHEMA EXTRACT")
    output.append("-- ==========================================\n")
    
    # 1. Functions
    output.append("-- Functions:")
    with engine.connect() as conn:
        res = conn.execute(text("""
            SELECT p.proname, pg_get_functiondef(p.oid) AS ddl
            FROM pg_proc p
            JOIN pg_namespace n ON p.pronamespace = n.oid
            WHERE n.nspname = 'public' 
            AND p.prokind = 'f' 
            AND p.proowner <> 10;
        """))
        for row in res:
            # exclude some standard or built-in noise, proowner <> 10 helps mostly
            if not row.proname.startswith('gen_'):
                output.append(f"{row.ddl};\n")

    # 2. Tables
    # We will sort tables to respect FK dependencies if possible, but for a simple dump we'll just list them out
    # For a perfect script we might just list them without FKs first, then add ALTER TABLE.
    # We will build standard CREATE TABLE statements.
    
    # Let's get dependencies
    tables = inspector.get_table_names()
    
    for table in tables:
        output.append(f"-- Table: {table}")
        cols = inspector.get_columns(table)
        pk = inspector.get_pk_constraint(table)
        pk_cols = pk.get('constrained_columns', [])
        
        create_stmt = f"CREATE TABLE IF NOT EXISTS {table} (\n"
        col_defs = []
        for col in cols:
            col_name = col['name']
            col_type = col['type'].compile(engine.dialect)
            default = col.get('default')
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            
            def_str = ""
            if default is not None:
                def_str = f" DEFAULT {default}"
            
            col_defs.append(f"    {col_name} {col_type} {nullable}{def_str}")
        
        if pk_cols:
            pk_name = pk.get('name')
            pk_name_str = f"CONSTRAINT {pk_name} " if pk_name else ""
            col_defs.append(f"    {pk_name_str}PRIMARY KEY ({', '.join(pk_cols)})")
            
        create_stmt += ",\n".join(col_defs)
        create_stmt += "\n);\n"
        output.append(create_stmt)
    
    # 3. Foreign Keys
    output.append("-- Foreign Keys:")
    for table in tables:
        fks = inspector.get_foreign_keys(table)
        for fk in fks:
            fk_name = fk.get('name')
            constrained = ", ".join(fk['constrained_columns'])
            referred_table = fk['referred_table']
            referred_columns = ", ".join(fk['referred_columns'])
            
            fk_stmt = f"ALTER TABLE {table} ADD CONSTRAINT {fk_name} FOREIGN KEY ({constrained}) REFERENCES {referred_table} ({referred_columns});"
            output.append(fk_stmt)
            
    output.append("\n")

    # 4. Triggers
    output.append("-- Triggers:")
    with engine.connect() as conn:
        res = conn.execute(text("""
            SELECT pg_get_triggerdef(t.oid) as ddl
            FROM pg_trigger t
            JOIN pg_class c ON t.tgrelid = c.oid
            JOIN pg_namespace n ON c.relnamespace = n.oid
            WHERE n.nspname = 'public' AND t.tgisinternal = false;
        """))
        for row in res:
            output.append(f"{row.ddl};\n")

    out_path = os.path.join(os.getcwd(), 'scratch', 'introspect_schema.sql')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(output))
    print(f"Schema fully extracted to {out_path}")

if __name__ == "__main__":
    generate_ddl()
