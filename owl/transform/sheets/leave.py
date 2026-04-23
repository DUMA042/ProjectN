"""
owl.transform.sheets.leave
~~~~~~~~~~~~~~~~~~~~~~~~~
Decomposes Leave data into LeaveTypes and EmployeeLeave records.
"""

from __future__ import annotations

import pandas as pd
from owl.transform.normalizer import BaseNormalizer, NormalizationResult
from owl.logger import get_logger

log = get_logger(__name__)

class LeaveNormalizer(BaseNormalizer):
    """
    Normalizer for Leave Records.
    Ensures leave types are deduplicated and linked to employees.
    """

    def decompose(self) -> NormalizationResult:
        df = self._source.copy()
        valid_ids = self._context.get("valid_ids", set())
        
        entities = {}
        
        # 1. Standardise and Clean
        df.columns = [str(c).lower().strip().replace(" ", "_") for c in df.columns]
        
        if "id_no" not in df.columns:
            raise KeyError("Required column 'id_no' not found in Leave sheet.")
        
        df["id_no"] = df["id_no"].astype(str).str.strip()
        
        # 2. Handle Orphans (Records for IDs not in 'employees' table)
        mask_orphan = ~df["id_no"].isin(valid_ids)
        orphans = df[mask_orphan]
        valid_recs = df[~mask_orphan].copy()
        
        if len(orphans) > 0:
            self._warn(f"Quarantined {len(orphans)} leave record(s) with unknown id_no.")
            # Depending on requirements, we could add a quarantine_leaves table
            # For now, we skip them to preserve integrity.
            
        # 3. Extract Dimension: leave_types
        # Column in sheet is 'leave_type'
        lt_df, lt_lookup = self._build_dim(valid_recs, ["leave_type"], id_column="leave_type_id")
        
        # Map back to DB table name 'leave_types'
        # Note: LT_DF columns will be ['leave_type_id', 'leave_type']
        # We should rename 'leave_type' to 'leave_type_name' to match model
        lt_df = lt_df.rename(columns={"leave_type": "leave_type_name"})
        entities["leave_types"] = lt_df
        
        # 4. Fact Table: employee_leaves
        fact_df = valid_recs.copy()
        fact_df["leave_type_id"] = fact_df["leave_type"].map(lambda x: lt_lookup.get((x,)))
        
        # Ensure dates
        fact_df["start_date"] = pd.to_datetime(fact_df["start_date"]).dt.date
        if "end_date" in fact_df.columns:
            fact_df["end_date"] = pd.to_datetime(fact_df["end_date"]).dt.date
        else:
            fact_df["end_date"] = None
            
        final_cols = ["id_no", "leave_type_id", "start_date", "end_date"]
        entities["employee_leaves"] = fact_df[final_cols].drop_duplicates()
        
        return NormalizationResult(entities=entities, warnings=self._warnings)
