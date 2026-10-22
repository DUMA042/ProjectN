"""Strict query-param parsing: malformed input is rejected, never ignored.

Silently defaulting to {} on bad JSON hides caller bugs and can return
unfiltered (wider-than-asked) data. Every filter-bearing endpoint uses this.
"""
from __future__ import annotations

import json

from fastapi import HTTPException


def parse_json_object_param(raw: str | None, name: str = "filters") -> dict:
    """Parse a JSON-object query param; 422 on malformed/non-object input."""
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid JSON in '{name}' — expected an object like "
            f"'{{\"department\": [\"HR\"]}}'.",
        ) from None
    if not isinstance(parsed, dict):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid '{name}' — expected a JSON object.",
        )
    return parsed
