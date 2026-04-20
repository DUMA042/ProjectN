"""
owl.analyze.statistical_models
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Python-based statistical and data-science workflows.

Approach
--------
SQL handles aggregations efficiently at the database level.
These functions take the resulting DataFrames and apply higher-order
statistical modelling that SQL cannot express cleanly:
  * Descriptive statistics with confidence intervals.
  * Trend analysis (OLS regression for attendance rates over time).
  * Anomaly detection (Z-score based outlier flagging).
  * Forecasting scaffold (extensible for time-series models).

All functions are pure (DataFrame in → DataFrame / dict out) and stateless.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from owl.logger import get_logger

log = get_logger(__name__)


# ── Descriptive statistics ────────────────────────────────────────────────────

def describe_attendance(df: pd.DataFrame, numeric_col: str) -> dict:
    """Compute descriptive statistics with 95% confidence interval.

    Parameters
    ----------
    df:
        DataFrame containing a numeric attendance metric column.
    numeric_col:
        Name of the numeric column to analyse.

    Returns
    -------
    dict
        Keys: mean, median, std, min, max, ci_lower, ci_upper, n.
    """
    series = df[numeric_col].dropna()
    n = len(series)
    if n == 0:
        log.warning(f"describe_attendance: no data in column '{numeric_col}'.")
        return {}

    mean = series.mean()
    std = series.std(ddof=1)
    ci = stats.t.interval(0.95, df=n - 1, loc=mean, scale=stats.sem(series))

    log.debug(
        f"describe_attendance[{numeric_col}]: n={n}, mean={mean:.2f}, ci={ci}."
    )
    return {
        "n": n,
        "mean": round(float(mean), 4),
        "median": round(float(series.median()), 4),
        "std": round(float(std), 4),
        "min": round(float(series.min()), 4),
        "max": round(float(series.max()), 4),
        "ci_lower": round(float(ci[0]), 4),
        "ci_upper": round(float(ci[1]), 4),
    }


# ── Trend analysis ────────────────────────────────────────────────────────────

def compute_attendance_trend(
    df: pd.DataFrame,
    time_col: str,
    rate_col: str,
) -> dict:
    """Fit an OLS linear regression to detect attendance trends over time.

    Parameters
    ----------
    df:
        DataFrame with a time index and an attendance rate column.
    time_col:
        Column containing time periods (converted to ordinal integers).
    rate_col:
        Column containing the attendance rate (0–100 float).

    Returns
    -------
    dict
        Keys: slope, intercept, r_squared, p_value, is_significant.
        ``is_significant`` is True when p_value < 0.05.
    """
    clean = df[[time_col, rate_col]].dropna()
    if len(clean) < 3:
        log.warning("compute_attendance_trend: insufficient data points (need ≥ 3).")
        return {}

    # Convert time to ordinal if it is a date.
    x = pd.to_datetime(clean[time_col]).map(pd.Timestamp.toordinal) \
        if clean[time_col].dtype == "object" else clean[time_col].astype(float)
    y = clean[rate_col].astype(float)

    slope, intercept, r_value, p_value, _ = stats.linregress(x, y)

    log.debug(
        f"compute_attendance_trend: slope={slope:.4f}, R²={r_value**2:.4f}, p={p_value:.4f}."
    )
    return {
        "slope": round(float(slope), 6),
        "intercept": round(float(intercept), 4),
        "r_squared": round(float(r_value ** 2), 4),
        "p_value": round(float(p_value), 6),
        "is_significant": bool(p_value < 0.05),
    }


# ── Anomaly detection ─────────────────────────────────────────────────────────

def flag_attendance_anomalies(
    df: pd.DataFrame,
    rate_col: str,
    z_threshold: float = 2.0,
) -> pd.DataFrame:
    """Flag rows where the attendance rate deviates more than *z_threshold* σ.

    Parameters
    ----------
    df:
        DataFrame with an attendance rate column.
    rate_col:
        Name of the numeric attendance rate column.
    z_threshold:
        Z-score cutoff (default 2.0 ≈ 95th percentile outlier).

    Returns
    -------
    pd.DataFrame
        Original DataFrame with two new columns:
        ``z_score``    — Z-score of each row's rate value.
        ``is_anomaly`` — Boolean flag.
    """
    df = df.copy()
    series = df[rate_col].astype(float)
    df["z_score"] = np.abs(stats.zscore(series.fillna(series.mean())))
    df["is_anomaly"] = df["z_score"] > z_threshold

    anomaly_count = df["is_anomaly"].sum()
    if anomaly_count:
        log.warning(
            f"flag_attendance_anomalies: {anomaly_count} anomaly(ies) detected "
            f"in '{rate_col}' at |z| > {z_threshold}."
        )
    return df
