"""
Occupancy Features module for ParkZenith Feature Engineering.
Implements calculations for lags, rolling averages, differences, trends, and growth rates.
"""

import logging
from typing import List, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def generate_occupancy_features(
    df: pd.DataFrame,
    percentage_col: str = "occupancy_percentage",
    occupied_col: str = "occupied_slots",
    total_col: str = "total_slots",
    timestamp_col: str = "collected_at",
    lag_periods: Optional[List[int]] = None,
    rolling_windows: Optional[List[int]] = None,
) -> pd.DataFrame:
    """
    Generates occupancy features: previous occupancy, difference, growth rate, rolling mean/max/min,
    occupancy trend, and lag features.
    Handles multiple facilities and zones by grouping properly.
    """
    if lag_periods is None:
        # Default lags (e.g., 1, 2, 3, 4, 12, 24 periods)
        lag_periods = [1, 2, 3, 4, 12, 24]
    if rolling_windows is None:
        # Default rolling windows (e.g., 3, 6, 12, 24 periods)
        rolling_windows = [3, 6, 12, 24]

    df_feat = df.copy()

    # Fill nullable zone_id for reliable grouping
    if "zone_id" in df_feat.columns:
        df_feat["_group_zone"] = df_feat["zone_id"].fillna("ALL_ZONES")
        group_cols = ["facility_id", "_group_zone"]
    else:
        group_cols = ["facility_id"]

    # Ensure chronological order within groups
    df_feat = df_feat.sort_values(by=group_cols + [timestamp_col])

    # 1. Base Occupancy Percentage
    if percentage_col not in df_feat.columns and occupied_col in df_feat.columns and total_col in df_feat.columns:
        df_feat[percentage_col] = (df_feat[occupied_col] / df_feat[total_col] * 100.0).round(4)
    elif percentage_col not in df_feat.columns:
        # If columns missing, cannot compute occupancy percentage features
        logger.warning("Occupancy percentage column not found and could not be calculated. Skipping occupancy feature generation.")
        return df_feat

    # 2. Previous Occupancy & Lags
    groupby_obj = df_feat.groupby(group_cols)

    # Previous occupancy is lag 1
    df_feat["prev_occupancy"] = groupby_obj[percentage_col].shift(1)
    
    # Lag features
    for lag in lag_periods:
        df_feat[f"occupancy_lag_{lag}"] = groupby_obj[percentage_col].shift(lag)

    # 3. Occupancy Difference
    df_feat["occupancy_diff"] = df_feat[percentage_col] - df_feat["prev_occupancy"]

    # 4. Occupancy Growth Rate
    # Growth rate relative to previous value. Use small epsilon to avoid division by zero.
    df_feat["occupancy_growth_rate"] = (
        (df_feat[percentage_col] - df_feat["prev_occupancy"])
        / (df_feat["prev_occupancy"].replace(0, np.nan))
    ).fillna(0.0)

    # 5. Rolling average, moving average, max, and min
    for window in rolling_windows:
        # min_periods=1 allows calculation for initial rows rather than forcing NaN
        df_feat[f"occupancy_roll_mean_{window}"] = (
            groupby_obj[percentage_col]
            .rolling(window=window, min_periods=1)
            .mean()
            .reset_index(level=list(range(len(group_cols))), drop=True)
        )
        df_feat[f"occupancy_roll_max_{window}"] = (
            groupby_obj[percentage_col]
            .rolling(window=window, min_periods=1)
            .max()
            .reset_index(level=list(range(len(group_cols))), drop=True)
        )
        df_feat[f"occupancy_roll_min_{window}"] = (
            groupby_obj[percentage_col]
            .rolling(window=window, min_periods=1)
            .min()
            .reset_index(level=list(range(len(group_cols))), drop=True)
        )

    # 6. Occupancy Trend (Difference between short-term and long-term moving averages)
    # E.g. 3-period rolling mean vs 12-period rolling mean
    short_roll = "occupancy_roll_mean_3"
    long_roll = "occupancy_roll_mean_12"
    if short_roll in df_feat.columns and long_roll in df_feat.columns:
        df_feat["occupancy_trend"] = df_feat[short_roll] - df_feat[long_roll]
    else:
        df_feat["occupancy_trend"] = 0.0

    # Cleanup temporary grouping column
    if "_group_zone" in df_feat.columns:
        df_feat = df_feat.drop(columns=["_group_zone"])

    logger.info("Generated occupancy features with %d lags and %d rolling windows.", len(lag_periods), len(rolling_windows))
    return df_feat
