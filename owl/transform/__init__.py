"""
owl.transform
~~~~~~~~~~~~~
Layer 2 — Data cleaning and 3NF normalisation.

Public surface
--------------
DataCleaner        : Low-level, stateless cleaning operations on DataFrames.
Normalizer         : Decomposes a cleaned DataFrame into 3NF entity dictionaries.
(validators)       : Pydantic models enforcing the contract between Transform → Load.
"""
