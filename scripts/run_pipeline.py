"""
scripts/run_pipeline.py
~~~~~~~~~~~~~~~~~~~~~~~~
CLI runner for the full owl pipeline.

Usage
-----
    python scripts/run_pipeline.py --file nest/attendance_2024.xlsx

Options are deliberately minimal — sheet classification is handled automatically
by the StructuralClassifier.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from owl.logger import get_logger
from owl.pipeline import Pipeline
from owl.extract.excel_reader import ExcelReader
from owl.extract.classifier import StructuralClassifier
from owl.extract.registry import NORMALIZER_REGISTRY

log = get_logger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the owl data pipeline for a given Excel source file."
    )
    parser.add_argument(
        "--file",
        required=True,
        help="Path to the Excel file (e.g. nest/attendance_2024.xlsx).",
    )
    parser.add_argument(
        "--sheets",
        nargs="*",
        default=None,
        help="Specific sheet names to process. Defaults to all sheets.",
    )
    parser.add_argument(
        "--header-row",
        type=int,
        default=1,
        help="Header row number (1-indexed). Default: 1.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    source = Path(args.file)
    
    if not source.exists():
        log.error(f"File not found: {source}")
        sys.exit(1)

    log.info(f"Auto-detecting file type for '{source.name}'...")
    
    # 1. Read a sample to classify the file structure
    try:
        reader = ExcelReader(source, header_row=None)
        frames_raw = reader.read()
    except Exception as e:
        log.error(f"Failed to read Excel file: {e}")
        sys.exit(1)
        
    identified_type = None
    
    if frames_raw:
        # Try to find a structural match on any sheet
        for sheet_name, df_raw in frames_raw.items():
            result = StructuralClassifier.find_best_header_row(df_raw)
            if result:
                report_type, _ = result
                identified_type = report_type
                log.info(f"Identified report type: {identified_type.value}")
                break
            
    if not identified_type:
        log.warning("Could not auto-detect report type from file contents.")
        log.warning("Only Extract will run \u2014 Transform and Load are skipped.")
        normalizer_class = None
    else:
        normalizer_class = NORMALIZER_REGISTRY.get(identified_type)
        if not normalizer_class:
            log.warning(f"No normalizer registered for type '{identified_type.value}'.")
            
    # Need valid employee IDs for the normalizer context to prevent orphans
    valid_ids = set()
    try:
        from owl.load.database import get_session
        from sqlalchemy import select
        with get_session() as session:
            from owl.load.models import Employee
            res = session.execute(select(Employee.id_no)).scalars().all()
            valid_ids = set(res)
    except Exception as e:
        log.warning(f"Could not load valid employee IDs context: {e}")

    # 2. Run Pipeline
    pipeline = Pipeline(
        source_file=source,
        normalizer_class=normalizer_class,
        sheet_names=args.sheets,
        header_row=args.header_row,
        context={"valid_ids": valid_ids}
    )
    pipeline.run()


if __name__ == "__main__":
    main()
