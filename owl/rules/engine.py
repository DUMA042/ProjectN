import json
import select
import threading
import time

from sqlalchemy import text

from owl.load.database import get_engine, get_session
from owl.logger import get_logger

log = get_logger(__name__)

# ── In-memory rules cache ─────────────────────────────────────────────────────
# The rules_settings table is the source of truth; this cache is kept in sync by
# (a) invalidating on our own writes and (b) a PostgreSQL LISTEN/NOTIFY listener
# that reacts to changes made by any process. Reads are served from memory and
# only hit the database when the cache has actually been invalidated.
_lock = threading.Lock()
_cache: dict | None = None


def _parse_value(raw):
    """Normalise a jsonb cell to a Python object.

    Newer rows store proper jsonb objects (psycopg2 returns dict/list). Older rows
    were double-encoded (a JSON string nested inside the jsonb), so they come back
    as a ``str`` — decode those here for backward compatibility.
    """
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return raw
    return raw


def load_rules() -> dict:
    """Read all rules directly from the database (bypasses the cache)."""
    with get_session() as s:
        rows = s.execute(
            text("SELECT rule_key, rule_value FROM rules_settings")
        ).fetchall()
    return {r[0]: _parse_value(r[1]) for r in rows}


def get_cached_rules() -> dict:
    """Return the cached rules, loading them once if the cache is empty."""
    global _cache
    if _cache is None:
        with _lock:
            if _cache is None:
                _cache = load_rules()
    return _cache


def invalidate_rules_cache() -> None:
    """Mark the cache stale; the next read reloads it from the database."""
    global _cache
    with _lock:
        _cache = None


def get_rule(key: str, default=None):
    return get_cached_rules().get(key, default)


def save_rule(key: str, value: dict | list | str | bool) -> None:
    with get_session() as s:
        s.execute(
            text("""
                INSERT INTO rules_settings (rule_key, rule_value)
                VALUES (:key, CAST(:value AS jsonb))
                ON CONFLICT (rule_key) DO UPDATE SET rule_value = CAST(:value AS jsonb), updated_at = NOW()
            """),
            # CAST(:value AS jsonb) parses the JSON exactly once (avoids double-encoding).
            {"key": key, "value": json.dumps(value)},
        )
        s.commit()
    invalidate_rules_cache()


def seed_defaults(defaults: dict, reset: bool = False) -> None:
    """Insert rule defaults.

    ``reset=False`` (default) only inserts missing keys (ON CONFLICT DO NOTHING).
    ``reset=True`` overwrites existing keys with the defaults (ON CONFLICT DO UPDATE).
    """
    conflict = (
        "ON CONFLICT (rule_key) DO UPDATE SET rule_value = CAST(:value AS jsonb), updated_at = NOW()"
        if reset
        else "ON CONFLICT (rule_key) DO NOTHING"
    )
    with get_session() as s:
        for key, value in defaults.items():
            s.execute(
                text(f"""
                    INSERT INTO rules_settings (rule_key, rule_value)
                    VALUES (:key, CAST(:value AS jsonb))
                    {conflict}
                """),
                {"key": key, "value": json.dumps(value)},
            )
        s.commit()
    invalidate_rules_cache()


# ── Database trigger ──────────────────────────────────────────────────────────
TRIGGER_DDL = [
    """
    CREATE OR REPLACE FUNCTION notify_rules_change() RETURNS trigger AS $$
    BEGIN
      PERFORM pg_notify('rules_changed', COALESCE(NEW.rule_key, OLD.rule_key));
      RETURN NULL;
    END;
    $$ LANGUAGE plpgsql;
    """,
    "DROP TRIGGER IF EXISTS trg_rules_changed ON rules_settings;",
    """
    CREATE TRIGGER trg_rules_changed
    AFTER INSERT OR UPDATE OR DELETE ON rules_settings
    FOR EACH ROW EXECUTE FUNCTION notify_rules_change();
    """,
]


def ensure_rules_trigger() -> None:
    """Create the NOTIFY trigger on rules_settings if it does not already exist."""
    try:
        with get_session() as s:
            for stmt in TRIGGER_DDL:
                s.execute(text(stmt))
            s.commit()
    except Exception as exc:  # noqa: BLE001 — must never crash startup
        log.warning(f"Could not ensure rules trigger: {exc}")


# ── LISTEN/NOTIFY listener ────────────────────────────────────────────────────
_listener_thread: threading.Thread | None = None
_listener_stop = threading.Event()

# Debounced analytics fact-table rebuild (rule changes affect attendance classification)
_rebuild_thread: threading.Thread | None = None
_rebuild_pending = threading.Event()


def _rebuild_worker() -> None:
    while not _listener_stop.is_set():
        _rebuild_pending.wait(timeout=1)
        if not _rebuild_pending.is_set():
            continue
        time.sleep(5)  # debounce rapid rule edits
        _rebuild_pending.clear()
        try:
            from owl.analytics.fact import rebuild_attendance_daily

            rebuild_attendance_daily()
            log.info("attendance_daily rebuilt after rule change")
        except Exception as exc:  # noqa: BLE001
            log.warning(f"Analytics fact rebuild failed: {exc}")


def schedule_fact_rebuild() -> None:
    """Request a debounced analytics fact-table rebuild."""
    _rebuild_pending.set()


def _listener_loop() -> None:
    while not _listener_stop.is_set():
        fairy = None
        try:
            fairy = get_engine().raw_connection()
            conn = getattr(fairy, "dbapi_connection", None) or fairy.connection
            conn.autocommit = True
            cur = conn.cursor()
            cur.execute("LISTEN rules_changed;")
            cur.close()
            log.info("Rules listener connected — LISTEN rules_changed")

            while not _listener_stop.is_set():
                if select.select([conn], [], [], 5)[0]:
                    conn.poll()
                    while conn.notifies:
                        note = conn.notifies.pop(0)
                        log.info(f"Rules changed (notify: {note.payload}) — invalidating cache")
                        invalidate_rules_cache()
                        schedule_fact_rebuild()
        except Exception as exc:  # noqa: BLE001
            log.warning(f"Rules listener error: {exc}; reconnecting in 2s")
            time.sleep(2)
        finally:
            try:
                if fairy is not None:
                    fairy.close()
            except Exception:  # noqa: BLE001
                pass


def start_rules_listener() -> None:
    global _listener_thread, _rebuild_thread
    if _listener_thread is not None and _listener_thread.is_alive():
        return
    _listener_stop.clear()
    _listener_thread = threading.Thread(target=_listener_loop, name="rules-listener", daemon=True)
    _listener_thread.start()
    if _rebuild_thread is None or not _rebuild_thread.is_alive():
        _rebuild_thread = threading.Thread(target=_rebuild_worker, name="rules-rebuild", daemon=True)
        _rebuild_thread.start()


def stop_rules_listener() -> None:
    _listener_stop.set()
