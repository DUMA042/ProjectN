import sys; from pathlib import Path; sys.path.insert(0, str(Path.cwd()))
import pandas as pd
files = sorted(Path("nest/card_Swiping_Folder").glob("AHRD_CardSwipe_202608_v*.xlsx"))
print(f"Found {len(files)} versions:")
for f in files:
    df = pd.read_excel(f, nrows=3)
    cols = list(df.columns)
    time_col = [c for c in cols if "time" in str(c).lower() or "swiping" in str(c).lower()][0] if any("time" in str(c).lower() or "swiping" in str(c).lower() for c in cols) else None
    if time_col:
        vals = df[time_col].head(2).tolist()
        types = [type(v).__name__ for v in vals]
        print(f"  {f.name}: cols={cols}, time_type={types}, samples={[str(v)[:30] for v in vals]}")
