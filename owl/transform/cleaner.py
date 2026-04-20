"""
owl.transform.cleaner
~~~~~~~~~~~~~~~~~~~~~
Stateless, composable data-cleaning operations.

Design principle
----------------
Every public function in this module is a *pure transformation*:
  input DataFrame → cleaned DataFrame.

No I/O, no side effects, no global state. This makes the functions trivially
testable and safely composable in any order.

Cleaning taxonomy
-----------------
1. Structural  : Drop fully-blank rows/columns, reset index.
2. String      : Strip whitespace, normalise case, strip invisible characters.
3. Type        : Coerce columns to expected dtypes where possible.
4. Null        : Strategy-based handling (drop, fill, flag) per column spec.
5. Duplicate   : Detect and remove or flag exact-duplicate rows.
"""

from __future__ import annotations

import re
from typing import Literal

import pandas as pd

from owl.logger import get_logger

log = get_logger(__name__)

NullStrategy = Literal["drop", "fill", "flag"]


# ── 1. Structural ─────────────────────────────────────────────────────────────

def drop_blank_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows where *every* cell is null or whitespace-only."""
    mask = df.apply(
        lambda row: row.map(lambda v: pd.isna(v) or (isinstance(v, str) and not v.strip())).all(),
        axis=1,
    )
    cleaned = df[~mask].reset_index(drop=True)
    removed = mask.sum()
    if removed:
        log.debug(f"drop_blank_rows: removed {removed} blank row(s).")
    return cleaned


def drop_blank_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Remove columns where *every* cell is null or whitespace-only."""
    def col_is_blank(series: pd.Series) -> bool:
        return series.map(lambda v: pd.isna(v) or (isinstance(v, str) and not v.strip())).all()

    blank_cols = [col for col in df.columns if col_is_blank(df[col])]
    if blank_cols:
        log.debug(f"drop_blank_columns: dropped {blank_cols}.")
    return df.drop(columns=blank_cols)


def reset_index(df: pd.DataFrame) -> pd.DataFrame:
    """Reset the DataFrame index to a clean integer range."""
    return df.reset_index(drop=True)


# ── 2. String normalisation ───────────────────────────────────────────────────

def strip_whitespace(df: pd.DataFrame) -> pd.DataFrame:
    """Strip leading/trailing whitespace from all string cells."""
    str_cols = df.select_dtypes(include="object").columns
    df = df.copy()
    df[str_cols] = df[str_cols].apply(lambda s: s.str.strip())
    return df


def remove_invisible_chars(df: pd.DataFrame) -> pd.DataFrame:
    """Remove zero-width spaces, non-breaking spaces, and other invisibles."""
    _invisible_pattern = re.compile(r"[\u200b\u200c\u200d\ufeff\xa0]+")

    def _clean(val: object) -> object:
        if isinstance(val, str):
            return _invisible_pattern.sub(" ", val).strip()
        return val

    str_cols = df.select_dtypes(include="object").columns
    df = df.copy()
    df[str_cols] = df[str_cols].apply(lambda s: s.map(_clean))
    return df


def normalise_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Standardise column names to snake_case, stripping special characters."""
    def _to_snake(name: str) -> str:
        name = re.sub(r"[^\w\s]", "", str(name))          # remove punctuation
        name = re.sub(r"\s+", "_", name.strip())           # spaces → underscore
        name = re.sub(r"_+", "_", name).lower()             # collapse underscores
        return name or "unnamed"

    df = df.copy()
    df.columns = [_to_snake(c) for c in df.columns]
    return df


# ── 3. Type coercion ─────────────────────────────────────────────────────────

def coerce_dates(df: pd.DataFrame, date_columns: list[str]) -> pd.DataFrame:
    """Attempt to parse *date_columns* as datetime, coercing errors to NaT."""
    df = df.copy()
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
            nat_count = df[col].isna().sum()
            if nat_count:
                log.warning(
                    f"coerce_dates: {nat_count} value(s) in '{col}' could not be parsed → NaT."
                )
    return df


def coerce_numerics(df: pd.DataFrame, numeric_columns: list[str]) -> pd.DataFrame:
    """Attempt to coerce *numeric_columns* to float, errors → NaN."""
    df = df.copy()
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            nan_count = df[col].isna().sum()
            if nan_count:
                log.warning(
                    f"coerce_numerics: {nan_count} value(s) in '{col}' could not be coerced → NaN."
                )
    return df


# ── 4. Null handling ─────────────────────────────────────────────────────────

def handle_nulls(
    df: pd.DataFrame,
    strategy: NullStrategy = "flag",
    fill_values: dict[str, object] | None = None,
    flag_column_suffix: str = "_is_missing",
) -> pd.DataFrame:
    """Apply a null-handling strategy.

    Parameters
    ----------
    df:
        Input DataFrame.
    strategy:
        * ``"drop"``  — Drop rows containing *any* null value.
        * ``"fill"``  — Fill nulls using *fill_values* mapping (col → fill val).
        * ``"flag"``  — Add a boolean ``<col>_is_missing`` column for each
                        column that contains nulls, then leave nulls in place.
    fill_values:
        Required when ``strategy="fill"``.  Maps column name → fill value.
    flag_column_suffix:
        Suffix for the flag columns added by ``strategy="flag"``.
    """
    df = df.copy()

    if strategy == "drop":
        before = len(df)
        df = df.dropna().reset_index(drop=True)
        log.debug(f"handle_nulls[drop]: removed {before - len(df)} row(s).")

    elif strategy == "fill":
        fill_values = fill_values or {}
        df = df.fillna(fill_values)

    elif strategy == "flag":
        null_cols = [c for c in df.columns if df[c].isna().any()]
        for col in null_cols:
            df[f"{col}{flag_column_suffix}"] = df[col].isna()
        if null_cols:
            log.debug(f"handle_nulls[flag]: flagged {len(null_cols)} column(s) with nulls.")

    return df


# ── 5. Duplicate handling ─────────────────────────────────────────────────────

def drop_duplicates(
    df: pd.DataFrame,
    subset: list[str] | None = None,
    keep: Literal["first", "last", False] = "first",
) -> pd.DataFrame:
    """Remove duplicate rows.

    Parameters
    ----------
    df:
        Input DataFrame.
    subset:
        Columns to consider for duplicate detection. ``None`` uses all.
    keep:
        Which duplicate to keep: ``'first'``, ``'last'``, or ``False`` (drop all).
    """
    before = len(df)
    df = df.drop_duplicates(subset=subset, keep=keep).reset_index(drop=True)
    removed = before - len(df)
    if removed:
        log.warning(f"drop_duplicates: removed {removed} duplicate row(s).")
    return df
