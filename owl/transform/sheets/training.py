"""
owl.transform.sheets.training
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Decomposes Training data and handles orphan detection (Option A).
"""

from __future__ import annotations

import pandas as pd
from owl.transform.normalizer import BaseNormalizer, NormalizationResult
from owl.logger import get_logger

log = get_logger(__name__)

class TrainingNormalizer(BaseNormalizer):
    """
    Normalizer for Training Records.
    Implements Option A: Quarantine records for unknown IDs.
    """

    def decompose(self) -> NormalizationResult:
        df = self._source
        valid_ids = self._context.get("valid_ids", set())
        
        entities = {}
        
        # 1. Orphans Detection (Option A)
        total_rows = len(df)
        df["id_no"] = df["id_no"].astype(str).str.strip()
        
        mask_orphan = ~df["id_no"].isin(valid_ids)
        orphans = df[mask_orphan]
        valid_recs = df[~mask_orphan]
        
        if len(orphans) > 0:
            msg = f"Option A: Quarantined {len(orphans)} training record(s) with unknown id_no."
            self._warn(msg)
            # We could store orphans in a separate 'quarantine' entity if we want
            entities["quarantine_training"] = orphans
            
        # 2. Extract Dimensions
        venue_df, venue_lookup = self._build_dim(valid_recs, ["venue"], id_column="venue_id")
        cons_df, cons_lookup = self._build_dim(valid_recs, ["consultant"], id_column="consultant_id")
        loc_df, loc_lookup = self._build_dim(valid_recs, ["location"], id_column="location_id")
        
        entities["venues"] = venue_df
        entities["consultants"] = cons_df
        entities["locations"] = loc_df
        
        # 3. Fact Table: employee_trainings
        fact_df = valid_recs.copy()
        fact_df["venue_id"] = fact_df["venue"].map(lambda x: venue_lookup.get((x,)))
        fact_df["consultant_id"] = fact_df["consultant"].map(lambda x: cons_lookup.get((x,)))
        fact_df["location_id"] = fact_df["location"].map(lambda x: loc_lookup.get((x,)))
        
        # Ensure date types
        fact_df["start_date"] = pd.to_datetime(fact_df["start_date"]).dt.date
        fact_df["end_date"] = pd.to_datetime(fact_df["end_date"]).dt.date
        
        final_cols = ["id_no", "venue_id", "consultant_id", "location_id", "start_date", "end_date"]
        entities["employee_trainings"] = fact_df[final_cols]
        
        return NormalizationResult(entities=entities, warnings=self._warnings)
