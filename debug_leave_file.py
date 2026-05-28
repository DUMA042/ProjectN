# debug_leave_file.py
import pandas as pd
from owl.extract.classifier import StructuralClassifier

file_path = "inbox/Leave testing 2705.xlsx"

# Read raw like the manager does
df_raw = pd.read_excel(file_path, header=None)

print(f"📊 File shape: {df_raw.shape[0]} rows × {df_raw.shape[1]} columns")

print(f"\n🔍 First 5 rows, signature columns only (indices: [2, 6, 7, 8, 10, 22, 24]):")
sig_cols = [2, 6, 7, 8, 10, 22, 24]
# ✅ Uses built-in .to_string() instead of .to_markdown() to avoid tabulate dependency
subset = df_raw.head(5).iloc[:, sig_cols]
print(subset.to_string())

print(f"\n🧪 Testing classifier validation:")
result = StructuralClassifier.validate_leave_file(df_raw)
print(f"Classifier returned: {result}")

print(f"\n🔎 Checking signature values manually:")
def check(val, expected) -> bool:
    return str(val).strip().upper().replace(" ", "") == str(expected).upper().replace(" ", "")

r1, r2 = df_raw.iloc[0], df_raw.iloc[1]

checks = [
    ("Major[8]", r1[8], "PRE-RETIREMENTLEAVE", check(r1[8], "PRE-RETIREMENTLEAVE")),
    ("Major[10]", r1[10], "CASUALBEFOREANNUAL", check(r1[10], "CASUALBEFOREANNUAL")),
    ("Major[22]", r1[22], "COMPASSIONATELEAVE", check(r1[22], "COMPASSIONATELEAVE")),
    ("Major[24]", r1[24], "PATERNITYLEAVE", check(r1[24], "PATERNITYLEAVE")),
    ("Sub[2]", r2[2], "STAFFID", check(r2[2], "STAFFID")),
    ("Sub[6]", r2[6], "PROPOSEDLEAVEDATE", check(r2[6], "PROPOSEDLEAVEDATE")),
    ("Sub[7]", r2[7], "RESUMPTIONDATE", check(r2[7], "RESUMPTIONDATE")),
]

for label, actual, expected, passed in checks:
    status = "✅" if passed else "❌"
    print(f"{status} {label}: actual='{actual}' | expected='{expected}' | match={passed}")