"""
owl.extract.registry
~~~~~~~~~~~~~~~~~~~~
Centralised registry for sheet types and their normalizers.
"""

from __future__ import annotations
from typing import TYPE_CHECKING
from owl.extract.classifier import ReportType

if TYPE_CHECKING:
    from owl.transform.normalizer import BaseNormalizer

from owl.transform.sheets.nominal import NominalNormalizer
from owl.transform.sheets.training import TrainingNormalizer
from owl.transform.sheets.card_swipe import CardSwipeNormalizer

# Mapping of ReportType to the concrete Normalizer class.
# Add entries here as new sheets are implemented.
NORMALIZER_REGISTRY: dict[ReportType, type[BaseNormalizer]] = {
    ReportType.NOMINAL: NominalNormalizer,
    ReportType.TRAINING: TrainingNormalizer,
    ReportType.CARD_SWIPE: CardSwipeNormalizer,
}
