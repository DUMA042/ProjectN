import os
from sqlalchemy import create_engine, inspect
from dotenv import load_dotenv

def check_id_no():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    engine = create_engine(db_url)
    inspector = inspect(engine)
    for tbl in inspector.get_table_names():
        for col in inspector.get_columns(tbl):
            if col['name'] == 'id_no':
                print(f"{tbl}.id_no: {col['type']}")

if __name__ == "__main__":
    check_id_no()
