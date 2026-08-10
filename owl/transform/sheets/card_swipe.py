"""
owl.transform.sheets.card_swipe
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Decomposes Card Swipe data and handles orphan detection (Option A).
"""

from __future__ import annotations

import pandas as pd
from owl.transform.normalizer import BaseNormalizer, NormalizationResult
from owl.logger import get_logger

log = get_logger(__name__)

class CardSwipeNormalizer(BaseNormalizer):
    """
    Normalizer for Card Swipe Records.
    Implements Option A: Quarantine records for unknown IDs.
    """

    def decompose(self) -> NormalizationResult:
        df = self._source.copy()
        
        # Ensure column names are snake_case for robust mapping
        df.columns = [str(c).lower().strip().replace(" ", "_") for c in df.columns]
        
        name_to_id = self._context.get("name_to_id", {})
        unmapped_names = self._context.get("unmapped_names", set())
        entities = {}
        
        # 1. Standardise identifiers/columns
        if "attendance_terminal" in df.columns and "location" not in df.columns:
            df["location"] = df["attendance_terminal"]
            
        if "attendance_time" in df.columns and "swipe_time" not in df.columns:
            df["swipe_time"] = df["attendance_time"]
        elif "card_swiping_time" in df.columns and "swipe_time" not in df.columns:
            df["swipe_time"] = df["card_swiping_time"]

        # Ensure name exists
        if "name" not in df.columns:
            raise KeyError(f"Required column 'name' not found. Columns found: {df.columns.tolist()}")

        # Clean name column for checking
        df["name_clean"] = df["name"].astype(str).str.lower().str.strip().str.replace(r"\s+", " ", regex=True)
        
        # Map known names to IDs
        df["mapped_id_no"] = df["name_clean"].map(name_to_id)
        
        # Mask orphans (unmapped)
        mask_orphan = df["mapped_id_no"].isna()
        orphans = df[mask_orphan].copy()
        valid_recs = df[~mask_orphan].copy()
        
        if len(orphans) > 0:
            msg = f"Option A: Quarantined {len(orphans)} card swipe record(s) with unmapped name."
            self._warn(msg)
            
            # Record unmapped names globally
            for idx, u_name in orphans["name"].dropna().items():
                if str(u_name).strip():
                    unmapped_names.add(str(u_name).strip())
            
            # Map columns to match QuarantineCardSwipe model
            q_df = orphans
            q_df["employee_name"] = q_df["name"]
            if "location" in q_df.columns:
                q_df["location_name"] = q_df["location"]
            
            # Only exact matching schema columns
            q_cols = ["employee_name", "swipe_time"]
            if "location_name" in q_df.columns:
                q_cols.append("location_name")
                
            entities["quarantine_card_swipes"] = q_df[q_cols].copy()
            
        # 2. Fact Table: employee_card_swipes
        if not valid_recs.empty:
            fact_df = valid_recs
        
            # Remap columns strictly
            fact_df["id_no"] = fact_df["mapped_id_no"]
            fact_df["location_id"] = 1  # Forced location hardcoding
            
            # Ensure swipe_time is datetime (DD/MM/YYYY format)
            fact_df["swipe_time"] = pd.to_datetime(fact_df["swipe_time"], dayfirst=True)
            
            final_cols = ["id_no", "location_id", "swipe_time"]
            entities["employee_card_swipes"] = fact_df[final_cols].copy()
            
        return NormalizationResult(entities=entities, warnings=self._warnings)
