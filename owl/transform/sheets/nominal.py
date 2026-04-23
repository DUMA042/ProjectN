"""
owl.transform.sheets.nominal
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Decomposes Nominal Roll into Employee and related dimension DataFrames.
"""

from __future__ import annotations

import pandas as pd
from datetime import date
from owl.transform.normalizer import BaseNormalizer, NormalizationResult
from owl.logger import get_logger

log = get_logger(__name__)

class NominalNormalizer(BaseNormalizer):
    """
    Normalizer for the Master Nominal Roll.
    Handles extraction of Employees, Units, Ranks, Departments, etc.
    """

    def decompose(self) -> NormalizationResult:
        df = self._source.copy()
        
        # Standardize headers to snake_case before operations
        df.columns = (
            pd.Series(df.columns).str.lower()
            .str.strip()
            .str.replace(r"\s+", "_", regex=True)
            .str.replace(r"[^\w\s]", "", regex=True)
        )
        
        entities = {}
        
        # 1. Extract Dimension Tables
        rank_df, rank_lookup = self._build_dim(df, ["rank"], id_column="rank_id")
        unit_df, unit_lookup = self._build_dim(df, ["unit"], id_column="unit_id")
        status_df, status_lookup = self._build_dim(df, ["status"], id_column="status_id")
        type_df, type_lookup = self._build_dim(df, ["employment_type"], id_column="emp_type_id")
        location_df, location_lookup = self._build_dim(df, ["location"], id_column="location_id")
        
        # NEW DIMS
        dept_df, dept_lookup = self._build_dim(df, ["department"], id_column="department_id")
        gl_df, gl_lookup = self._build_dim(df, ["gl"], id_column="gl_id")
        
        entities["ranks"] = rank_df
        entities["units"] = unit_df
        entities["employee_statuses"] = status_df
        entities["employment_types"] = type_df
        entities["locations"] = location_df
        entities["departments"] = dept_df.rename(columns={"department": "department_name"})
        entities["grade_levels"] = gl_df.rename(columns={"gl": "gl_name"})
        
        # 2. Extract Core Entity: Employees
        emp_df = df.copy()
        
        # Map IDs
        emp_df["rank_id"] = emp_df["rank"].map(lambda x: rank_lookup.get((x,)))
        emp_df["unit_id"] = emp_df["unit"].map(lambda x: unit_lookup.get((x,)))
        emp_df["status_id"] = emp_df["status"].map(lambda x: status_lookup.get((x,)))
        emp_df["emp_type_id"] = emp_df["employment_type"].map(lambda x: type_lookup.get((x,)))
        emp_df["location_id"] = emp_df["location"].map(lambda x: location_lookup.get((x,)))
        emp_df["department_id"] = emp_df["department"].map(lambda x: dept_lookup.get((x,)))
        emp_df["gl_id"] = emp_df["gl"].map(lambda x: gl_lookup.get((x,)))
        
        # Natural Key and Mandatory Serial No
        emp_df["id_no"] = emp_df["id_no"].astype(str).str.strip()
        
        # Serial No handling: Check for 'sn', 's_n', or fallback to a counter if missing but NOT NULL
        def _get_safe_sn(val, idx):
            try:
                ov = int(float(val))
                return ov if ov > 0 else idx + 100000 
            except:
                return idx + 100000

        if "sn" in emp_df.columns:
            emp_df["serial_no"] = [_get_safe_sn(v, i) for i, v in enumerate(emp_df["sn"])]
        elif "s_n" in emp_df.columns:
            emp_df["serial_no"] = [_get_safe_sn(v, i) for i, v in enumerate(emp_df["s_n"])]
        else:
            emp_df["serial_no"] = range(100000, 100000 + len(emp_df))

        # Handle sex/gender if present
        if "sex" not in emp_df.columns and "gender" in emp_df.columns:
            emp_df["sex"] = emp_df["gender"]

        # Final column set for the 'employees' table
        final_cols = [
            "id_no", "serial_no", "full_name", "sex", "rank_id", 
            "unit_id", "status_id", "emp_type_id", "location_id", "remark"
        ]
        
        # Ensure 'remark' column exists
        if "remark" not in emp_df.columns:
            emp_df["remark"] = None

        # Clean Rows
        output_df = emp_df.drop_duplicates(subset=["id_no"])
        # Clean Rows
        output_df = emp_df.drop_duplicates(subset=["id_no"])
        
        # Final column set for the 'employees' table (History is now automated in DB)
        final_cols = [
            "id_no", "serial_no", "full_name", "sex", "rank_id", 
            "unit_id", "status_id", "emp_type_id", "location_id", 
            "department_id", "gl_id", "remark"
        ]
        
        entities["employees"] = output_df[[c for c in final_cols if c in output_df.columns]]
        
        return NormalizationResult(entities=entities, warnings=self._warnings)
