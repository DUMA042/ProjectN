import sys
import traceback
from owl.ingest.worker import IngestionWorker

worker = IngestionWorker()
try:
    worker.run_once()
    print("Worker finished")
except Exception as e:
    traceback.print_exc()
