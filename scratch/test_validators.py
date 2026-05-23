import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from owl.transform.validators import validate_dataframe

# Test 1: Valid training data
df_good = pd.DataFrame({
    'id_no': ['EMP001', 'EMP002'],
    'venue_id': [1, 2],
    'consultant_id': [1, 1],
    'location_id': [1, 1],
    'start_date': [pd.Timestamp('2024-01-01'), pd.Timestamp('2024-02-01')],
    'end_date': [pd.Timestamp('2024-01-31'), pd.Timestamp('2024-02-28')]
})
valid_df, errors = validate_dataframe('employee_trainings', df_good)
print(f"Test 1 (all valid): {len(valid_df)} passed, {len(errors)} errors")

# Test 2: Bad data — 'NOT_A_DATE' in start_date
df_bad = pd.DataFrame({
    'id_no': ['EMP001', 'EMP002', 'EMP003'],
    'venue_id': [1, 2, 3],
    'consultant_id': [1, 1, 1],
    'location_id': [1, 1, 1],
    'start_date': [pd.Timestamp('2024-01-01'), 'NOT_A_DATE', pd.Timestamp('2024-03-01')],
    'end_date': [pd.Timestamp('2024-01-31'), pd.Timestamp('2024-02-28'), pd.Timestamp('2024-03-31')]
})
valid_df2, errors2 = validate_dataframe('employee_trainings', df_bad)
print(f"Test 2 (one bad date): {len(valid_df2)} passed, {len(errors2)} errors")
for e in errors2:
    print(f"  -> {e['message']}")

# Test 3: Unknown table (should pass through)
df_unknown = pd.DataFrame({'col1': [1, 2, 3]})
valid_df3, errors3 = validate_dataframe('nonexistent_table', df_unknown)
print(f"Test 3 (unknown table): {len(valid_df3)} passed, {len(errors3)} errors (passthrough)")

print("\nAll tests complete!")
