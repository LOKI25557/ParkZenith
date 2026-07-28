"""
Trend generation and rolling averages using Pandas.
"""

from typing import Dict, Any, List
import pandas as pd


def calculate_occupancy_rolling_average(df: pd.DataFrame, window: int = 3) -> List[Dict[str, Any]]:
    """
    Computes a rolling average of occupancy percentage over historical records.
    Assumes df is ordered by collected_at.
    """
    if df.empty:
        return []

    df_sorted = df.sort_values("collected_at").copy()
    
    # Calculate rolling mean
    df_sorted["rolling_occupancy"] = (
        df_sorted["occupancy_percentage"]
        .rolling(window=window, min_periods=1)
        .mean()
        .round(2)
    )

    trend = []
    for _, row in df_sorted.iterrows():
        collected_at_val = row["collected_at"]
        if isinstance(collected_at_val, pd.Timestamp):
            collected_at_str = collected_at_val.isoformat()
        else:
            collected_at_str = str(collected_at_val)

        trend.append({
            "collected_at": collected_at_str,
            "occupancy_percentage": float(round(row["occupancy_percentage"], 2)),
            "rolling_occupancy_percentage": float(row["rolling_occupancy"]),
        })

    return trend
