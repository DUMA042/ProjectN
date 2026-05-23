"""
owl.pipeline
~~~~~~~~~~~~
Top-level orchestrator — ties Extract → Transform → Validate → Load → Analyse together.

Design
------
The ``Pipeline`` class is the single entry point for running a full
end-to-end data flow for one Excel source file.  It delegates to the
layer sub-packages and surfaces errors with full context.

Usage
-----
    from owl.pipeline import Pipeline

    pipeline = Pipeline(source_file="nest/attendance_2024.xlsx")
    pipeline.run()
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from owl.config import settings
from owl.exceptions import OwlBaseError
from owl.extract.excel_reader import ExcelReader
from owl.load.database import get_session, verify_connection
from owl.load.loader import DataLoader
from owl.logger import get_logger
from owl.transform.validators import validate_dataframe

if TYPE_CHECKING:
    from owl.transform.normalizer import BaseNormalizer

log = get_logger(__name__)


class Pipeline:
    """End-to-end ETL orchestrator for a single Excel source.

    Parameters
    ----------
    source_file:
        Path to the Excel file inside ``nest/`` (relative or absolute).
    normalizer_class:
        A concrete subclass of ``BaseNormalizer`` specific to this file's
        layout.  Provided by the sheet package (e.g.
        ``sheets.attendance_2024.normalizer.AttendanceNormalizer``).
    sheet_names:
        Specific sheet names to process. ``None`` processes all sheets.
    header_row:
        Default header row for ``ExcelReader``.

    Example
    -------
    >>> from sheets.attendance_2024.normalizer import AttendanceNormalizer
    >>> Pipeline(
    ...     source_file="nest/attendance_2024.xlsx",
    ...     normalizer_class=AttendanceNormalizer,
    ... ).run()
    """

    def __init__(
        self,
        source_file: str | Path,
        normalizer_class: type["BaseNormalizer"] | None = None,
        sheet_names: list[str] | None = None,
        header_row: int = 1,
        ingestion_id: str | None = None,
        context: dict | None = None,
    ) -> None:
        self._source_file = Path(source_file)
        self._normalizer_class = normalizer_class
        self._sheet_names = sheet_names
        self._header_row = header_row
        self._ingestion_id = ingestion_id
        self._context = context or {}

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self) -> dict[str, Any]:
        """Execute the full ETL pipeline.

        Returns
        -------
        dict[str, Any]
            Summary of the pipeline execution results.
        """
        log.info(f"Pipeline started for '{self._source_file.name}'" + 
                 (f" (Ingestion ID: {self._ingestion_id})" if self._ingestion_id else ""))
        
        summary = {
            "source_file": str(self._source_file),
            "ingestion_id": self._ingestion_id,
            "status": "completed",
            "validation_results": {},
            "load_results": {}
        }

        try:
            verify_connection()
            frames = self._extract()
            entities = self._transform(frames)
            entities, validation_errors = self._validate(entities)
            load_reports = self._load(entities)
            
            # Populate validation results in the summary
            total_rejected = sum(len(errs) for errs in validation_errors.values())
            summary["validation_results"] = {
                "total_rejected": total_rejected,
                "errors_by_table": {
                    table: [
                        {"row": e["row_index"], "field": e["field"], "message": e["message"]}
                        for e in errs
                    ]
                    for table, errs in validation_errors.items()
                    if errs
                }
            }

            summary["load_results"] = {
                table: {
                    "success": report.success_count,
                    "failed": len(report.failed_rows)
                } for table, report in load_reports.items()
            }
            
            log.info(f"Pipeline completed successfully for '{self._source_file.name}'.")
            return summary
        except OwlBaseError as exc:
            summary["status"] = "failed"
            summary["error"] = str(exc)
            summary["error_context"] = exc.context
            return summary
        except Exception as exc:
            summary["status"] = "failed"
            summary["error"] = str(exc)
            log.exception("Unexpected pipeline error.")
            raise

    # ── Private helpers ───────────────────────────────────────────────────────

    def _extract(self):
        """Layer 1: Read raw Excel → dict of DataFrames."""
        log.info("Layer 1 — Extract: reading Excel file.")
        reader = ExcelReader(
            file_path=self._source_file,
            sheet_names=self._sheet_names,
            header_row=self._header_row,
        )
        frames = reader.read()
        log.info(f"Extracted {len(frames)} sheet(s).")
        return frames

    def _transform(self, frames):
        """Layer 2 & 3 (Transform): clean + normalise all sheets."""
        if self._normalizer_class is None:
            log.warning("No normalizer_class provided — skipping Transform stage.")
            return {}

        log.info("Layer 2 — Transform: cleaning and normalising.")
        combined_entities = {}
        for sheet_name, df in frames.items():
            log.info(f"Normalising sheet: '{sheet_name}'.")
            normalizer = self._normalizer_class(df, context=self._context)
            result = normalizer.decompose()
            for warning in result.warnings:
                log.warning(f"[{sheet_name}] {warning}")
            combined_entities.update(result.entities)

        log.info(f"Produced {len(combined_entities)} entity table(s).")
        return combined_entities

    def _validate(self, entities: dict) -> tuple[dict, dict]:
        """Layer 2.5 — Validate: check every row against Pydantic contracts.

        Parameters
        ----------
        entities:
            Dict of {table_name: DataFrame} from the normalizer.

        Returns
        -------
        tuple[dict, dict]
            - Cleaned entities dict (bad rows removed).
            - Dict of {table_name: [error_dicts]} for audit logging.
        """
        if not entities:
            return entities, {}

        log.info("Layer 2.5 — Validate: checking data against Pydantic contracts.")
        validated_entities = {}
        all_errors: dict[str, list] = {}

        for table_name, df in entities.items():
            valid_df, errors = validate_dataframe(table_name, df)
            validated_entities[table_name] = valid_df
            all_errors[table_name] = errors

        total_rejected = sum(len(errs) for errs in all_errors.values())
        if total_rejected:
            log.warning(f"Validation complete: {total_rejected} total row(s) rejected across all tables.")
        else:
            log.info("Validation complete: all rows passed.")

        return validated_entities, all_errors

    def _load(self, entities) -> dict[str, Any]:
        """Layer 3 (Load): persist normalised entities to PostgreSQL."""
        if not entities:
            log.warning("No entities to load — skipping Load stage.")
            return {}

        log.info("Layer 3 — Load: persisting to database.")
        with get_session() as session:
            loader = DataLoader(session, robust=True)
            results = loader.load(entities)
            for table, report in results.items():
                log.info(f"  {table}: {report.success_count} row(s) upserted, {len(report.failed_rows)} row(s) failed.")
            return results
