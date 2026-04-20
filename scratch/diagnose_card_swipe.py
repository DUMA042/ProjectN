from owl.pipeline import Pipeline
from owl.load.database import get_session
from owl.load.models import FileIngestionMeta
from sqlalchemy import select
from owl.extract.excel_reader import ExcelReader
from owl.extract.classifier import ReportType

with get_session() as session:
    # Find the failed CardSwipe job
    job = session.execute(
        select(FileIngestionMeta).where(FileIngestionMeta.original_filename.like("AttendanceSwiping%")).where(FileIngestionMeta.status == "failed")
    ).scalars().first()
    
    if not job:
        print("No failed card swipe job found.")
        exit()
        
    print(f"Diagnosing job: {job.original_filename}")
    
    # Run the pipeline directly to catch the exception
    pipeline = Pipeline(
        file_path=job.file_path,
        report_type=ReportType.CARD_SWIPE,
        ingestion_id=str(job.id)
    )
    
    try:
        # We manually run the extraction to see where it fails
        # Layer 1 & 2
        reader = ExcelReader(job.file_path, header_row=0) # Manager found it at row 0
        df = reader.read()["Sheet"]
        print("Read successful. Columns:", df.columns.tolist())
        
        # Layer 3: Normalization
        from owl.transform.sheets.card_swipe import CardSwipeNormalizer
        norm = CardSwipeNormalizer(df, context={"valid_ids": set()}) # Set empty context for now
        res = norm.decompose()
        print("Normalization successful.")
        
        # Layer 4: Loading
        from owl.load.loader import DataLoader
        with get_session() as load_session:
            loader = DataLoader(load_session, robust=True)
            report = loader.load(res.entities)
            print("Loading result:", report)
            load_session.commit()
            print("COMMIT SUCCESSFUL.")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
