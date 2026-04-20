import sys
from pathlib import Path
from sqlalchemy import text
from owl.load.database import get_session

def check_db():
    with get_session() as session:
        result = session.execute(text("SELECT original_filename, status, error_context, created_at FROM file_ingestion_meta ORDER BY created_at DESC LIMIT 3;"))
        for row in result:
            print(dict(row._mapping))

if __name__ == "__main__":
    check_db()
