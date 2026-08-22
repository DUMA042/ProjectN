import pandas as pd
vals = ["2026-08-03 06:05:35", "2026-08-07 22:03:22", "03/08/2026 06:05:35", "08/03/2026 06:05:35"]
for v in vals:
    with_df = pd.to_datetime(v, dayfirst=True)
    without_df = pd.to_datetime(v, dayfirst=False)
    print(f"Input: {v}")
    print(f"  dayfirst=True  -> {with_df}")
    print(f"  dayfirst=False -> {without_df}")
    print()
