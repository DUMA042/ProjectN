# owl 🦉 — Attendance Data Pipeline

> **Extract → Transform (3NF) → Load (PostgreSQL) → Analyse**
> Python 3.12+ · Pandas · openpyxl · SQLAlchemy · Pydantic v2

---

## Project Layout

```
AttendanceN/
├── nest/               ← Excel source files (git-ignored)
├── owl/                ← Main Python package
│   ├── config.py       ← Pydantic-Settings config singleton
│   ├── exceptions.py   ← Typed exception hierarchy
│   ├── logger.py       ← Structured logging (Rich)
│   ├── pipeline.py     ← Top-level ETL orchestrator
│   ├── extract/        ← Layer 1: Excel ingestion
│   │   ├── excel_reader.py     ← Merged-cell handling, multi-sheet
│   │   └── schema_detector.py  ← Heuristic header detection
│   ├── transform/      ← Layer 2: Clean & normalise
│   │   ├── cleaner.py          ← Stateless cleaning functions
│   │   ├── normalizer.py       ← 3NF BaseNormalizer + dim helpers
│   │   └── validators.py       ← Pydantic v2 data contracts
│   ├── load/           ← Layer 3: Database persistence
│   │   ├── database.py         ← Engine / Session factory
│   │   ├── models.py           ← SQLAlchemy ORM models
│   │   ├── schema.sql          ← Idempotent DDL (source of truth)
│   │   └── loader.py           ← Upsert orchestration
│   └── analyze/        ← Layer 4: Aggregations & stats
│       ├── sql_queries.py      ← Named SQL aggregations → DataFrame
│       └── statistical_models.py ← scipy / statsmodels workflows
├── sheets/             ← Per-Excel-source packages (add as needed)
├── tests/              ← pytest suite (mirrors owl/ structure)
├── scripts/
│   ├── init_db.py      ← Initialise DB from schema.sql
│   └── run_pipeline.py ← CLI runner
├── .env.example        ← Environment variable template
├── pyproject.toml
├── requirements.txt
└── requirements-dev.txt
```

---

## Quick Start

### 1. Create & activate a virtual environment
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
# For development / tests
pip install -r requirements-dev.txt
```

### 3. Configure environment
```bash
copy .env.example .env
# Edit .env and fill in DATABASE_URL
```

### 4. Initialise the database
```bash
python scripts/init_db.py
```

### 5. Drop an Excel file into `nest/` and run the pipeline
```bash
python scripts/run_pipeline.py --file nest/your_file.xlsx
```

---

## Adding a New Excel Source

1. Drop the `.xlsx` file into `nest/`.
2. Create a package under `sheets/`:

```
sheets/
└── your_file_name/
    ├── __init__.py
    ├── extractor.py     ← Column-mapping overrides
    ├── cleaner.py       ← Sheet-specific cleaning rules
    ├── normalizer.py    ← Subclass BaseNormalizer, implement decompose()
    └── loader.py        ← Sheet-specific load orchestration
```

3. Register the normalizer in `scripts/run_pipeline.py` → `SHEET_REGISTRY`.
4. Extend `owl/load/models.py` and `owl/load/schema.sql` with any new tables.

---

## Running Tests
```bash
pytest
```

---

## Architecture Principles

| Principle | How it's applied |
|---|---|
| **3NF** | Dimension tables for every repeating group; no denormalised columns in ORM. |
| **Error isolation** | Typed exceptions per pipeline layer (`ExtractionError`, `TransformationError`, etc.). |
| **No unvalidated writes** | Pydantic v2 models validate every record before it reaches the DB. |
| **Idempotent DDL** | `CREATE TABLE IF NOT EXISTS` — safe to re-run `init_db.py` at any time. |
| **Upsert semantics** | `INSERT … ON CONFLICT DO UPDATE` — pipeline is re-runnable without duplicates. |
| **Separation of concerns** | Each file handles exactly one concern; shared logic lives in `owl/` layers. |
