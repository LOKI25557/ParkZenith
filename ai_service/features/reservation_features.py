"""
Reservation Features module for ParkZenith Feature Engineering.
Implements calculations for reservation durations, cancellations, trends, and aggregations.
"""

import logging
from typing import Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def generate_reservation_transaction_features(
    df: pd.DataFrame,
    start_col: str = "reservation_start",
    end_col: str = "reservation_end",
    duration_col: str = "duration_minutes",
    status_col: str = "reservation_status",
    collected_col: str = "collected_at",
) -> pd.DataFrame:
    """
    Generates features for individual reservation transaction records.
    """
    df_feat = df.copy()

    # Convert timestamps
    for col in [start_col, end_col, collected_col]:
        if col in df_feat.columns:
            df_feat[col] = pd.to_datetime(df_feat[col], utc=True)

    # 1. Duration (minutes)
    if duration_col not in df_feat.columns and start_col in df_feat.columns and end_col in df_feat.columns:
        df_feat[duration_col] = (df_feat[end_col] - df_feat[start_col]).dt.total_seconds() / 60.0

    # 2. Lead Time (minutes between reservation collection/creation and start)
    if start_col in df_feat.columns and collected_col in df_feat.columns:
        df_feat["lead_time_minutes"] = (
            (df_feat[start_col] - df_feat[collected_col]).dt.total_seconds() / 60.0
        ).clip(lower=0.0)

    # 3. Status flags
    if status_col in df_feat.columns:
        df_feat["is_cancelled"] = (df_feat[status_col].astype(str).str.upper() == "CANCELLED").astype(int)
        df_feat["is_completed"] = (df_feat[status_col].astype(str).str.upper() == "COMPLETED").astype(int)
        df_feat["is_active"] = (df_feat[status_col].astype(str).str.upper() == "ACTIVE").astype(int)

    # 4. Hourly/Daily features based on start time
    if start_col in df_feat.columns:
        df_feat["start_hour"] = df_feat[start_col].dt.hour
        df_feat["start_dayofweek"] = df_feat[start_col].dt.dayofweek

    logger.info("Generated transaction-level features for %d reservations.", len(df_feat))
    return df_feat


def aggregate_reservation_features_hourly(
    df: pd.DataFrame,
    start_col: str = "reservation_start",
    duration_col: str = "duration_minutes",
    status_col: str = "reservation_status",
    capacity_col: Optional[str] = None,
    total_slots_default: int = 100,
) -> pd.DataFrame:
    """
    Aggregates reservation transactions to hourly intervals per facility.
    Generates:
      - reservations_in_prev_hour
      - reservations_today
      - reservation_density
      - reservation_trend
      - cancellation_rate
      - average_reservation_duration
      - reservation_growth
      - rolling_reservation_average
    """
    df_feat = df.copy()
    if len(df_feat) == 0:
        # Return empty DataFrame with expected structure
        return pd.DataFrame(columns=[
            "facility_id", "timestamp", "reservation_count", "reservations_in_prev_hour",
            "reservations_today", "reservation_density", "reservation_trend",
            "cancellation_rate", "average_reservation_duration", "reservation_growth",
            "rolling_res_avg_3h", "rolling_res_avg_6h", "rolling_res_avg_12h"
        ])

    df_feat[start_col] = pd.to_datetime(df_feat[start_col], utc=True)
    
    # Add dummy/categorical checks
    df_feat["is_cancelled"] = (df_feat[status_col].astype(str).str.upper() == "CANCELLED").astype(int)
    df_feat["res_count"] = 1

    # Round start time to nearest hour
    df_feat["timestamp"] = df_feat[start_col].dt.floor("h")

    # Group by facility and timestamp (hour)
    grouped = df_feat.groupby(["facility_id", "timestamp"]).agg(
        reservation_count=("res_count", "sum"),
        cancelled_count=("is_cancelled", "sum"),
        total_duration=(duration_col, "sum"),
    ).reset_index()

    # Reindex to complete hourly timeseries per facility to avoid gaps
    facilities = grouped["facility_id"].unique()
    resampled_dfs = []
    
    for fac in facilities:
        fac_df = grouped[grouped["facility_id"] == fac].set_index("timestamp")
        if len(fac_df) == 0:
            continue
        
        # Complete time index
        min_time = fac_df.index.min()
        max_time = fac_df.index.max()
        full_idx = pd.date_range(start=min_time, end=max_time, freq="h", tz="UTC")
        
        fac_df = fac_df.reindex(full_idx)
        fac_df["facility_id"] = fac
        fac_df["reservation_count"] = fac_df["reservation_count"].fillna(0.0)
        fac_df["cancelled_count"] = fac_df["cancelled_count"].fillna(0.0)
        fac_df["total_duration"] = fac_df["total_duration"].fillna(0.0)
        fac_df.index.name = "timestamp"
        resampled_dfs.append(fac_df.reset_index())

    if not resampled_dfs:
        return pd.DataFrame()

    aggregated = pd.concat(resampled_dfs, ignore_index=True)

    # Sort
    aggregated = aggregated.sort_values(by=["facility_id", "timestamp"])
    agg_groupby = aggregated.groupby("facility_id")

    # 1. Reservations in previous hour
    aggregated["reservations_in_prev_hour"] = agg_groupby["reservation_count"].shift(1).fillna(0.0)

    # 2. Reservations today (cumulative reservations starting since midnight)
    aggregated["reservations_today"] = (
        aggregated.groupby(["facility_id", aggregated["timestamp"].dt.date])["reservation_count"]
        .cumsum()
    )

    # 3. Average duration
    # Avoid zero division
    aggregated["average_reservation_duration"] = (
        aggregated["total_duration"] / aggregated["reservation_count"].replace(0, np.nan)
    ).fillna(0.0)

    # 4. Cancellation rate
    aggregated["cancellation_rate"] = (
        aggregated["cancelled_count"] / aggregated["reservation_count"].replace(0, np.nan)
    ).fillna(0.0)

    # 5. Reservation density
    # active reservations in this hour divided by total slots
    # For now, if we don't have slots dynamically, use default capacity
    capacity = total_slots_default
    aggregated["reservation_density"] = aggregated["reservation_count"] / capacity

    # 6. Reservation trend (current count - previous hour count)
    aggregated["reservation_trend"] = aggregated["reservation_count"] - aggregated["reservations_in_prev_hour"]

    # 7. Reservation growth (percentage change)
    aggregated["reservation_growth"] = (
        (aggregated["reservation_count"] - aggregated["reservations_in_prev_hour"])
        / aggregated["reservations_in_prev_hour"].replace(0, np.nan)
    ).fillna(0.0)

    # 8. Rolling reservation average (e.g., 3h, 6h, 12h)
    for window in [3, 6, 12]:
        aggregated[f"rolling_res_avg_{window}h"] = (
            agg_groupby["reservation_count"]
            .rolling(window=window, min_periods=1)
            .mean()
            .reset_index(level=0, drop=True)
        )

    # Drop intermediate columns
    aggregated = aggregated.drop(columns=["cancelled_count", "total_duration"])

    logger.info("Aggregated reservation features to hourly level. Count: %d rows.", len(aggregated))
    return aggregated
