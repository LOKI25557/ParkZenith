"""
Session Features module for ParkZenith Feature Engineering.
Implements individual session duration features and hourly entry/exit/occupancy aggregations.
"""

import logging
from typing import Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def generate_session_transaction_features(
    df: pd.DataFrame,
    check_in_col: str = "check_in_time",
    check_out_col: str = "check_out_time",
    duration_col: str = "duration_minutes",
    fee_col: str = "parking_fee",
) -> pd.DataFrame:
    """
    Generates features for individual parking session transactions.
    """
    df_feat = df.copy()

    # Convert timestamps
    for col in [check_in_col, check_out_col]:
        if col in df_feat.columns:
            df_feat[col] = pd.to_datetime(df_feat[col], utc=True)

    # 1. Duration (minutes) for completed sessions
    if duration_col in df_feat.columns and check_in_col in df_feat.columns and check_out_col in df_feat.columns:
        completed_mask = df_feat[check_out_col].notna()
        df_feat.loc[completed_mask, duration_col] = (
            (df_feat.loc[completed_mask, check_out_col] - df_feat.loc[completed_mask, check_in_col])
            .dt.total_seconds() / 60.0
        ).clip(lower=0.0)

    # 2. Time components of check-in
    if check_in_col in df_feat.columns:
        df_feat["check_in_hour"] = df_feat[check_in_col].dt.hour
        df_feat["check_in_dayofweek"] = df_feat[check_in_col].dt.dayofweek

    # 3. Revenue rate ($ per minute)
    if fee_col in df_feat.columns and duration_col in df_feat.columns:
        df_feat["revenue_per_minute"] = (
            df_feat[fee_col] / df_feat[duration_col].replace(0, np.nan)
        ).fillna(0.0)

    logger.info("Generated transaction-level features for %d sessions.", len(df_feat))
    return df_feat


def aggregate_session_features_hourly(
    df: pd.DataFrame,
    check_in_col: str = "check_in_time",
    check_out_col: str = "check_out_time",
    duration_col: str = "duration_minutes",
    fee_col: str = "parking_fee",
    total_slots_default: int = 100,
) -> pd.DataFrame:
    """
    Aggregates session transactions to hourly intervals per facility.
    Generates:
      - entry_rate (count of check-ins in the hour)
      - exit_rate (count of check-outs in the hour)
      - sessions_per_hour (active/parked vehicles in the hour)
      - sessions_per_day (cumulative check-ins since midnight)
      - average_session_duration
      - median_duration
      - average_revenue_per_session
      - parking_turnover (completed sessions / capacity)
      - session_density (active sessions / capacity)
    """
    df_feat = df.copy()
    if len(df_feat) == 0:
        return pd.DataFrame(columns=[
            "facility_id", "timestamp", "entry_rate", "exit_rate", "sessions_per_hour",
            "sessions_per_day", "average_session_duration", "median_duration",
            "average_revenue_per_session", "parking_turnover", "session_density"
        ])

    # Convert columns to datetime
    df_feat[check_in_col] = pd.to_datetime(df_feat[check_in_col], utc=True)
    if check_out_col in df_feat.columns:
        df_feat[check_out_col] = pd.to_datetime(df_feat[check_out_col], utc=True)
    else:
        df_feat[check_out_col] = pd.NaT

    # Generate rounded hour columns
    df_feat["check_in_hour_floor"] = df_feat[check_in_col].dt.floor("h")
    df_feat["check_out_hour_floor"] = df_feat[check_out_col].dt.floor("h")

    # Get full range of hours per facility
    facilities = df_feat["facility_id"].unique()
    resampled_dfs = []

    for fac in facilities:
        fac_df = df_feat[df_feat["facility_id"] == fac]
        if len(fac_df) == 0:
            continue

        min_time = fac_df[check_in_col].min().floor("h")
        max_time = fac_df[check_in_col].max().floor("h")
        
        # Max of checkouts too if applicable
        valid_checkouts = fac_df[check_out_col].dropna()
        if len(valid_checkouts) > 0:
            max_time = max(max_time, valid_checkouts.max().floor("h"))

        full_idx = pd.date_range(start=min_time, end=max_time, freq="h", tz="UTC")

        # Create base frame
        base_frame = pd.DataFrame(index=full_idx)
        base_frame.index.name = "timestamp"
        base_frame["facility_id"] = fac

        # 1. Entry rate (check-ins per hour)
        entries = fac_df.groupby("check_in_hour_floor").size()
        base_frame["entry_rate"] = base_frame.index.map(entries).fillna(0.0)

        # 2. Exit rate (check-outs per hour)
        exits = fac_df.dropna(subset=[check_out_col]).groupby("check_out_hour_floor").size()
        base_frame["exit_rate"] = base_frame.index.map(exits).fillna(0.0)

        # 3. Cumulative entries today (sessions per day so far)
        base_frame["sessions_per_day"] = (
            base_frame.groupby(base_frame.index.date)["entry_rate"]
            .cumsum()
        )

        # 4. Completed session metrics: duration and revenue per check-out hour
        checkout_metrics = fac_df.dropna(subset=[check_out_col]).groupby("check_out_hour_floor").agg(
            avg_duration=(duration_col, "mean"),
            median_duration=(duration_col, "median"),
            avg_fee=(fee_col, "mean"),
            completed_count=(duration_col, "count")
        )
        
        base_frame = base_frame.join(checkout_metrics, how="left")
        base_frame["average_session_duration"] = base_frame["avg_duration"].fillna(0.0)
        base_frame["median_duration"] = base_frame["median_duration"].fillna(0.0)
        base_frame["average_revenue_per_session"] = base_frame["avg_fee"].fillna(0.0)
        completed_counts = base_frame["completed_count"].fillna(0.0)
        base_frame = base_frame.drop(columns=["avg_duration", "median_duration", "avg_fee", "completed_count"])

        # 5. Parking turnover (completed sessions in the hour / capacity)
        capacity = total_slots_default
        base_frame["parking_turnover"] = completed_counts / capacity

        # 6. Active sessions (density & count)
        # Compute how many vehicles are active/parked during each hourly bin
        # A session is active in hour H if: check_in <= H and (check_out is null or check_out > H)
        active_counts = []
        for ts in base_frame.index:
            # Check if check-in is before or equal to this timestamp, and checkout is after this timestamp or null
            active_mask = (fac_df[check_in_col] <= ts) & (
                fac_df[check_out_col].isna() | (fac_df[check_out_col] > ts)
            )
            active_counts.append(active_mask.sum())

        base_frame["sessions_per_hour"] = active_counts
        base_frame["session_density"] = base_frame["sessions_per_hour"] / capacity

        resampled_dfs.append(base_frame.reset_index())

    if not resampled_dfs:
        return pd.DataFrame()

    aggregated = pd.concat(resampled_dfs, ignore_index=True)
    aggregated = aggregated.sort_values(by=["facility_id", "timestamp"])

    logger.info("Aggregated session features to hourly level. Count: %d rows.", len(aggregated))
    return aggregated
