from owl.load.models import Base
from owl.load.database import get_engine

print("Creating tables in database...")
Base.metadata.create_all(bind=get_engine())
print("Done!")
