import os
from sqlalchemy import create_engine, MetaData

db_url = "postgresql+psycopg2://postgres:1234@localhost:5433/flowdb"
engine = create_engine(db_url)
metadata = MetaData()
metadata.reflect(bind=engine)

for table_name in metadata.tables:
    table = metadata.tables[table_name]
    print(f"Table: {table_name}")
    for column in table.columns:
        print(f"  - {column.name}: {column.type} (nullable={column.nullable}, primary_key={column.primary_key})")
    print()
