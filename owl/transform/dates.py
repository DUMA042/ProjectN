"""Single home for the DD/MM/YYYY date business rule.

HR Excel files use day-first dates. Parsing is ISO-first (strict, unambiguous)
with a day-first fallback, so mixed-format files can never break either way —
the August 2026 incident (blanket dayfirst flags added, then ripped out while
debugging mixed ISO + DD/MM input) must not recur: every date site below
delegates here instead of carrying its own flags.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandas as pd
from dateutil.parser import parse as _parse_dateutil


def parse_dayfirst(value: Any) -> date | None:
    """Parse one cell to a date, or None when unparseable.

    datetime/date pass through; blanks/NaN give None; strings try strict ISO
    first, then day-first DD/MM/YYYY; anything else gives None (never raises).
    """
    if value is None or value is pd.NaT:  # NaT subclasses datetime: check first
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        if bool(pd.isna(value)):
            return None
    except (TypeError, ValueError):
        pass
    s = str(value).strip()
    if not s or s.lower() == "nan":
        return None
    try:
        return date.fromisoformat(s)
    except (ValueError, TypeError):
        pass
    try:
        # Space-separated datetimes ("2026-08-03 06:05:35"): dateutil with
        # dayfirst would swap month/day even after a year, so prefer ISO.
        return datetime.fromisoformat(s).date()
    except (ValueError, TypeError):
        pass
    try:
        return _parse_dateutil(s, dayfirst=True).date()
    except (ValueError, TypeError, OverflowError):
        return None


def coerce_dayfirst(series: pd.Series) -> pd.Series:
    """Vectorized two-pass parse for a string column: strict ISO first, then
    day-first for whatever remains. Unparseable entries become NaT."""
    iso = pd.to_datetime(series, format="ISO8601", errors="coerce")
    missing = iso.isna()
    if not missing.any():
        return iso
    second = pd.to_datetime(series[missing], dayfirst=True, errors="coerce")
    iso.loc[missing] = second
    return iso
