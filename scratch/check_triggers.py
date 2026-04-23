import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

def check_triggers():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    engine = create_engine(db_url)
    with engine.connect() as conn:
        res = conn.execute(text("""
            SELECT 
                tgname AS trigger_name, 
                relname AS table_name,
                pg_get_triggerdef(pg_trigger.oid) AS definition
            FROM pg_trigger 
            JOIN pg_class ON pg_trigger.tgrelid = pg_class.oid 
            WHERE NOT tgisinternal;
        """))
        for row in res:
            print(f"Trigger: {row.trigger_name} ON {row.table_name}")
            print(f"Definition: {row.definition}\n")
            
            # Extract function name from definition
            import re
            match = re.search(r"EXECUTE (?:FUNCTION|PROCEDURE) ([\w\.]+)\(\)", row.definition)
            if match:
                func_name = match.group(1).split('.')[-1]
                func_res = conn.execute(text(f"SELECT pg_get_functiondef(p.oid) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace WHERE p.proname = '{func_name}';"))
                print(f"Function: {func_name}")
                print(f"{func_res.scalar()}\n")

if __name__ == "__main__":
    check_triggers()
