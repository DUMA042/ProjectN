import json
from functools import lru_cache
from sqlalchemy import text
from owl.load.database import get_session


def load_rules() -> dict:
    with get_session() as s:
        rows = s.execute(
            text("SELECT rule_key, rule_value FROM rules_settings")
        ).fetchall()
    return {r[0]: r[1] for r in rows}


@lru_cache(maxsize=1)
def get_cached_rules() -> dict:
    return load_rules()


def invalidate_rules_cache():
    get_cached_rules.cache_clear()


def get_rule(key: str, default=None):
    rules = get_cached_rules()
    return rules.get(key, default)


def save_rule(key: str, value: dict | list | str | bool) -> None:
    with get_session() as s:
        s.execute(
            text("""
                INSERT INTO rules_settings (rule_key, rule_value)
                VALUES (:key, :value)
                ON CONFLICT (rule_key) DO UPDATE SET rule_value = :value, updated_at = NOW()
            """),
            {"key": key, "value": json.dumps(value)},
        )
        s.commit()
    invalidate_rules_cache()


def seed_defaults(defaults: dict) -> None:
    with get_session() as s:
        for key, value in defaults.items():
            s.execute(
                text("""
                    INSERT INTO rules_settings (rule_key, rule_value)
                    VALUES (:key, :value)
                    ON CONFLICT (rule_key) DO NOTHING
                """),
                {"key": key, "value": json.dumps(value)},
            )
        s.commit()
    invalidate_rules_cache()
