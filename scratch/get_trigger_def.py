import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

def get_function_def():
    load_dotenv()
    engine = create_engine(os.getenv('DATABASE_URL'))
    with engine.connect() as conn:
        res = conn.execute(text("SELECT pg_get_functiondef(oid) FROM pg_proc WHERE proname = 'log_combined_history'")).scalar()
        print(res)

if __name__ == "__main__":
    get_function_def()
