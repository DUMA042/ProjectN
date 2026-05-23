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
        
        # The Classifier looks for 'staff_id', so we must expect it
        if "staff_id" not in df.columns:
            raise KeyError("Required column 'staff_id' not found in Leave sheet.")
        
        # Rename staff_id to id_no internally for standard processing
        df = df.rename(columns={"staff_id": "id_no"})
        df["id_no"] = df["id_no"].astype(str).str.strip()
        
        # 2. Handle Orphans (Records for IDs not in 'employees' table)
        mask_orphan = ~df["id_no"].isin(valid_ids)
        orphans = df[mask_orphan]
        valid_recs = df[~mask_orphan].copy()
        
        if len(orphans) > 0:
            self._warn(f"Quarantined {len(orphans)} leave record(s) with unknown id_no.")
            # Depending on requirements, we could add a quarantine_leaves table
            # For now, we skip them to preserve integrity.
            
        if valid_recs.empty:
            return NormalizationResult(entities={}, warnings=self._warnings)
            
        # 3. Extract Dimension: leave_types
        # Column in sheet is usually 'leave_type'
        if "leave_type" in valid_recs.columns:
            lt_df, lt_lookup = self._build_dim(valid_recs, ["leave_type"], id_column="leave_type_id")
            lt_df = lt_df.rename(columns={"leave_type": "leave_type_name"})
            entities["leave_types"] = lt_df
            valid_recs["leave_type_id"] = valid_recs["leave_type"].map(lambda x: lt_lookup.get((x,)))
        else:
            valid_recs["leave_type_id"] = None

        # Helper to safely parse dates
        def _parse_date(col_name):
            if col_name in valid_recs.columns:
                return pd.to_datetime(valid_recs[col_name], errors="coerce").dt.date
            return None

        valid_recs["proposed_leave_date"] = _parse_date("proposed_leave_date")
        valid_recs["resumption_date"] = _parse_date("resumption_date")
        valid_recs["issuance_date"] = _parse_date("issuance_date")
        
        # Provide fallback defaults for raw fields if needed
        for col in ["forfeiture", "remark", "proposed_leave_date_raw", "issuance_date_raw"]:
            if col not in valid_recs.columns:
                valid_recs[col] = None
        
        # 4. Fact Table 1: leave_applications
        app_cols = [
            "id_no", "proposed_leave_date", "resumption_date", 
            "forfeiture", "issuance_date", "remark", 
            "proposed_leave_date_raw", "issuance_date_raw"
        ]
        entities["leave_applications"] = valid_recs[app_cols].drop_duplicates()
        
        # 5. Fact Table 2: leave_records
        # Map proposed_leave_date to start_date and resumption_date to end_date
        rec_df = valid_recs.copy()
        rec_df = rec_df.rename(columns={
            "proposed_leave_date": "start_date",
            "resumption_date": "end_date"
        })
        
        # Drop rows that don't have a start_date, as it's required in the schema
        rec_df = rec_df.dropna(subset=["start_date"])
        
        if not rec_df.empty:
            rec_cols = ["id_no", "leave_type_id", "start_date", "end_date"]
            entities["leave_records"] = rec_df[rec_cols].drop_duplicates()
        else:
            # Create empty DF with correct columns if all dates were invalid
            entities["leave_records"] = pd.DataFrame(columns=["id_no", "leave_type_id", "start_date", "end_date"])
        
        return NormalizationResult(entities=entities, warnings=self._warnings)
