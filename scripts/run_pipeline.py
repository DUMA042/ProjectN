"""
scripts/run_pipeline.py
~~~~~~~~~~~~~~~~~~~~~~~~
CLI runner for the full owl pipeline.

Usage
-----
    python scripts/run_pipeline.py --file nest/attendance_2024.xlsx

Options are deliberately minimal — sheet configuration is handled by the
sheet-specific package registered via ``SHEET_REGISTRY`` below.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from owl.logger import get_logger
from owl.pipeline import Pipeline

log = get_logger(__name__)

# ── Sheet registry ─────────────────────────────────────────────────────────────
# Map stem of the Excel filename to the sheet-specific normalizer class.
# Add an entry here each time a new sheet package is implemented.
#
# Example:
#   from sheets.attendance_2024.normalizer import AttendanceNormalizer
#   SHEET_REGISTRY = {
#       "attendance_2024": AttendanceNormalizer,
#   }

SHEET_REGISTRY: dict[str, type] = {}


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

    normalizer_class = SHEET_REGISTRY.get(source.stem)
    if normalizer_class is None:
        log.warning(
            f"No normalizer registered for '{source.stem}'. "
            "Only Extract will run — Transform and Load are skipped."
        )

    pipeline = Pipeline(
        source_file=source,
        normalizer_class=normalizer_class,
        sheet_names=args.sheets,
        header_row=args.header_row,
    )
    pipeline.run()


if __name__ == "__main__":
    main()
