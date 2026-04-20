from owl.ingest.manager import IngestionManager
from owl.extract.classifier import ReportType, IngestionMetadata
from pathlib import Path
from datetime import date

manager = IngestionManager()
meta = IngestionMetadata(report_type=ReportType.CARD_SWIPE, period=date(2026, 4, 1), version=2)
file_path = Path("nest/card_Swiping_Folder/AHRD_CardSwipe_202604_v2.xlsx")

try:
    manager._record_ingestion("original.xlsx", "new.xlsx", meta, "fakesum", file_path)
    print("Success!")
except Exception as e:
    import traceback
    traceback.print_exc()
