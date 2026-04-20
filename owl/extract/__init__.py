"""
owl.extract
~~~~~~~~~~~
Layer 1 — Raw data ingestion from Excel sources.

Public surface
--------------
ExcelReader        : Main entry point. Reads one Excel file → dict of DataFrames.
SchemaDetector     : Heuristic helper to locate headers in ambiguously formatted sheets.
"""
