# Database migrations (Alembic)

Single source of truth for schema *changes* is `migrations/versions/`.
`owl/load/schema.sql` remains the readable full-schema reference and the
fresh-install path (via `scripts/init_db.py`, safe to re-run).

## Fresh database

```bat
python scripts\init_db.py
alembic stamp 0001
```

(`init_db` builds everything; `stamp` records the baseline without
re-running it. `alembic upgrade head` on a fresh database works too.)

## Existing database (upgrade)

```bat
alembic current        &:: confirm where you are
alembic upgrade head   &:: apply pending migrations only
```

Migrations are guarded no-ops where already applied. If a migration fails
on data (e.g. a unique index meeting duplicate rows), it aborts loudly
with the offending key: clean the data, then re-run. Nothing is deleted
automatically.

## Rollback

```bat
alembic downgrade -1   &:: revert the last migration (data untouched,
                       :: except the 0001 baseline, whose downgrade drops
                       :: tables and is for test/disaster use only)
```

## Authoring a change

1. Change `owl/load/schema.sql` AND `owl/load/models.py` together
   (`tests/test_migrations/test_drift.py` fails if they diverge).
2. `alembic revision -m "<what>" --autogenerate`, review the diff,
   test up/down on a throwaway database before shipping.
3. `attendance_daily` is intentionally model-less (built by app code);
   `migrations/env.py` excludes it from autogenerate — never add it.
