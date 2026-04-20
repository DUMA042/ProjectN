"""
scripts/migrate_nominal.py
~~~~~~~~~~~~~~~~~~~~~~~~~~
Direct migration script to process all Excel files in the Norminal_Folder.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from owl.config import settings
from owl.logger import get_logger
from owl.pipeline import Pipeline
from owl.transform.sheets.nominal import NominalNormalizer
from owl.extract.classifier import StructuralClassifier

import pandas as pd

log = get_logger(__name__)

def main() -> None:
    target_dir = settings.nest_dir / "Norminal_Folder"
    
    if not target_dir.exists():
        log.error(f"Target directory does not exist: {target_dir}")
        return

    excel_files = list(target_dir.glob("*.xlsx"))
    if not excel_files:
        log.warning(f"No '.xlsx' files found in {target_dir}.")
        return

    log.info(f"Found {len(excel_files)} files to process in {target_dir.name}.")
    
    success_count = 0
    failure_count = 0

    for file_path in excel_files:
        try:
            log.info(f"=== Starting pipeline for: {file_path.name} ===")
            
            # Auto-detect floating headers
            df_raw = pd.read_excel(file_path, header=None)
            res = StructuralClassifier.find_best_header_row(df_raw)
            if not res:
                log.error(f"FATAL: Could not find FINGERPRINT headers in {file_path.name}")
                continue
            
            h_row = res[1]
            log.info(f"Automatically detected headers at row {h_row}")
            
            pipeline = Pipeline(
                source_file=file_path,
                normalizer_class=NominalNormalizer,
                sheet_names=None,
                header_row=h_row, 
            )
            
            result = pipeline.run()
            status = result.get("status")
            
            if status == "completed":
                load_results = result.get("load_results", {})
                for table, counts in load_results.items():
                    log.info(
                        f"  -> {table}: "
                        f"{counts.get('success', 0)} loaded, "
                        f"{counts.get('failed', 0)} failed"
                    )
                success_count += 1
            else:
                log.error(f"Pipeline failed for {file_path.name}: {result.get('error')}")
                failure_count += 1
                
        except Exception as exc:
            log.exception(f"Unexpected error processing {file_path.name}: {exc}")
            failure_count += 1

    log.info("=== Migration Summary ===")
    log.info(f"Successfully processed: {success_count} file(s)")
    log.info(f"Failed to process: {failure_count} file(s)")

if __name__ == "__main__":
    main()
