"""
owl.transform.normalizer
~~~~~~~~~~~~~~~~~~~~~~~~
3NF decomposition scaffolding.

Responsibility
--------------
Accept a *cleaned* flat DataFrame (output of the cleaner) and decompose it into
a set of normalised entity DataFrames, one per relational table.

Design
------
The base class ``BaseNormalizer`` provides shared infrastructure:
  * Entity registry / tracking.
  * Surrogate-key assignment.
  * Deduplication across entities.

Sheet-specific normalizers (under ``sheets/<sheet_name>/normalizer.py``) inherit
from ``BaseNormalizer`` and implement ``decompose()``, which returns the full
``NormalizedEntities`` dict.

Why a class, not functions?
-----------------------------
Normalisation inherently carries *state* (surrogate-key counters, dimension
lookup tables) that must persist between rows of the same sheet.  A class
encapsulates this cleanly.
"""

from __future__ import annotations

import uuid
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from owl.logger import get_logger

log = get_logger(__name__)

# Canonical type alias: {table_name: DataFrame}
NormalizedEntities = dict[str, pd.DataFrame]


# ── Surrogate key utilities ───────────────────────────────────────────────────

def generate_surrogate_key(natural_key_str: str) -> int:
    """Generate a deterministic 32-bit integer surrogate key from a string."""
    return int(hashlib.md5(natural_key_str.encode("utf-8")).hexdigest(), 16) % (2**31 - 1)


def assign_surrogate_keys(df: pd.DataFrame, id_column: str = "id") -> pd.DataFrame:
    """Prepend a deterministic integer surrogate key column to *df*."""
    df = df.copy()
    keys = []
    for _, row in df.iterrows():
        # Combine all row values into a single string for hashing
        row_str = "|".join(str(val) for val in row.values)
        keys.append(generate_surrogate_key(row_str))
    
    df.insert(0, id_column, keys)
    return df


# ── Dimension-table helper ────────────────────────────────────────────────────

def build_dimension_table(
    source_df: pd.DataFrame,
    natural_key_columns: list[str],
    id_column: str = "id",
) -> tuple[pd.DataFrame, dict[Any, str]]:
    """Extract a dimension table from *source_df* and return a lookup map.

    Deduplicates on *natural_key_columns*, assigns a surrogate key to each
    unique combination, and returns both the dimension table and a mapping of
    natural key tuple → surrogate key (for FK assignment in fact rows).

    Parameters
    ----------
    source_df:
        The flat source DataFrame.
    natural_key_columns:
        Columns that uniquely identify a dimension row.
    id_column:
        Name of the surrogate key column in the output table.

    Returns
    -------
    dim_df:
        The deduplicated dimension DataFrame with surrogate keys.
    lookup:
        Dict mapping ``tuple(natural_key_values)`` → surrogate key string.
    """
    dim_df = (
        source_df[natural_key_columns]
        .drop_duplicates()
        .reset_index(drop=True)
    )
    dim_df = assign_surrogate_keys(dim_df, id_column=id_column)

    lookup: dict[Any, str] = {}
    for _, row in dim_df.iterrows():
        key = tuple(row[col] for col in natural_key_columns)
        lookup[key] = row[id_column]

    log.debug(
        f"build_dimension_table: built '{id_column}' dimension with {len(dim_df)} unique record(s)."
    )
    return dim_df, lookup


# ── Base normalizer ───────────────────────────────────────────────────────────

@dataclass
class NormalizationResult:
    """Container returned by ``BaseNormalizer.decompose()``."""

    entities: NormalizedEntities = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class BaseNormalizer(ABC):
    """Abstract base class for sheet-specific 3NF normalizers.

    Subclass this in ``sheets/<sheet_name>/normalizer.py`` and implement
    ``decompose()``.

    Parameters
    ----------
    source_df:
        The cleaned, flat DataFrame for the sheet being normalised.
    """

    def __init__(self, source_df: pd.DataFrame, context: dict | None = None) -> None:
        self._source = source_df.copy()
        self._context = context or {}
        self._warnings: list[str] = []

    @abstractmethod
    def decompose(self) -> NormalizationResult:
        """Decompose the flat source DataFrame into 3NF entity DataFrames.

        Returns
        -------
        NormalizationResult
            ``entities``  : dict of {table_name: DataFrame}
            ``warnings``  : list of non-fatal issues encountered.
        """
        ...

    # ── Shared helpers available to subclasses ────────────────────────────────

    def _warn(self, message: str) -> None:
        """Record a non-fatal normalisation warning."""
        log.warning(message)
        self._warnings.append(message)

    @staticmethod
    def _build_dim(
        source_df: pd.DataFrame,
        natural_key_columns: list[str],
        id_column: str = "id",
    ) -> tuple[pd.DataFrame, dict[Any, str]]:
        """Convenience alias for :func:`build_dimension_table`."""
        return build_dimension_table(source_df, natural_key_columns, id_column)

    @staticmethod
    def _assign_keys(df: pd.DataFrame, id_column: str = "id") -> pd.DataFrame:
        """Convenience alias for :func:`assign_surrogate_keys`."""
        return assign_surrogate_keys(df, id_column)
