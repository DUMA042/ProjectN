"""
owl.load
~~~~~~~~
Layer 3 — Persisting normalised data to PostgreSQL.

Public surface
--------------
get_engine / get_session : SQLAlchemy engine & session factory.
Base / ORM models        : Declarative ORM table definitions (mirrors schema.sql).
DataLoader               : Orchestrates upsert / bulk-insert operations.
"""
