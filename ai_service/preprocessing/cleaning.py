"""
Data Cleaning module for ParkZenith Preprocessing Pipeline.
Implements reusable functions for duplicates, missing values, timestamps, outliers,
occupancy-specific, reservation-specific, and session-specific cleaning.
"""

import logging
from typing import List, Optional, Union
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def remove_duplicates(df: pd.DataFrame, subset: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Removes duplicate records from the DataFrame.
    """
    before_count = len(df)
    df_cleaned = df.drop_duplicates(subset=subset, keep="first")
    after_count = len(df_cleaned)
    logger.info("Removed %d duplicate records.", before_count - after_count)
    return df_cleaned


def handle_missing_values(
    df: pd.DataFrame,
    strategy: str = "drop",
    columns: Optional[List[str]] = None,
    fill_value: Optional[Union[int, float, str]] = None,
) -> pd.DataFrame:
    """
    Handles missing values in specified columns using a given strategy: 'drop', 'mean', 'median', 'mode', or 'fill'.
    """
    if columns is None:
        columns = list(df.columns)

    df_cleaned = df.copy()

    for col in columns:
        if col not in df_cleaned.columns:
            continue
        missing_count = df_cleaned[col].isnull().sum()
        if missing_count == 0:
            continue

        if strategy == "drop":
            df_cleaned = df_cleaned.dropna(subset=[col])
            logger.info("Dropped %d records with missing values in column: %s", missing_count, col)
        elif strategy == "mean":
            if pd.api.types.is_numeric_dtype(df_cleaned[col]):
                mean_val = df_cleaned[col].mean()
                df_cleaned[col] = df_cleaned[col].fillna(mean_val)
                logger.info("Filled missing values in %s with mean: %s", col, mean_val)
        elif strategy == "median":
            if pd.api.types.is_numeric_dtype(df_cleaned[col]):
                median_val = df_cleaned[col].median()
                df_cleaned[col] = df_cleaned[col].fillna(median_val)
                logger.info("Filled missing values in %s with median: %s", col, median_val)
        elif strategy == "mode":
            mode_series = df_cleaned[col].mode()
            if not mode_series.empty:
                mode_val = mode_series.iloc[0]
                df_cleaned[col] = df_cleaned[col].fillna(mode_val)
                logger.info("Filled missing values in %s with mode: %s", col, mode_val)
        elif strategy == "fill" and fill_value is not None:
            df_cleaned[col] = df_cleaned[col].fillna(fill_value)
            logger.info("Filled missing values in %s with value: %s", col, fill_value)
        elif strategy == "ffill":
            df_cleaned[col] = df_cleaned[col].ffill()
            logger.info("Applied forward-fill to missing values in %s", col)
        elif strategy == "bfill":
            df_cleaned[col] = df_cleaned[col].bfill()
            logger.info("Applied backward-fill to missing values in %s", col)

    return df_cleaned


def validate_timestamps(df: pd.DataFrame, timestamp_cols: List[str]) -> pd.DataFrame:
    """
    Ensures timestamp columns are valid datetime objects.
    Drops rows with invalid (NaT) timestamps or future/implausible dates.
    """
    df_cleaned = df.copy()
    now = pd.Timestamp.now(tz="utc")

    for col in timestamp_cols:
        if col not in df_cleaned.columns:
            continue
        
        # Convert to datetime (with UTC timezone)
        df_cleaned[col] = pd.to_datetime(df_cleaned[col], errors="coerce", utc=True)
        
        # Count NaT
        nat_count = df_cleaned[col].isna().sum()
        if nat_count > 0:
            df_cleaned = df_cleaned.dropna(subset=[col])
            logger.info("Dropped %d records with invalid timestamps in column %s", nat_count, col)
            
        if len(df_cleaned) == 0:
            continue

        # Filter out future timestamps (more than 1 hour in the future to allow minor clock skew)
        future_mask = df_cleaned[col] > (now + pd.Timedelta(hours=1))
        future_count = future_mask.sum()
        if future_count > 0:
            df_cleaned = df_cleaned[~future_mask]
            logger.info("Dropped %d records with future timestamps in column %s", future_count, col)

        # Filter out extreme past timestamps (prior to year 2020)
        past_mask = df_cleaned[col] < pd.Timestamp("2020-01-01", tz="utc")
        past_count = past_mask.sum()
        if past_count > 0:
            df_cleaned = df_cleaned[~past_mask]
            logger.info("Dropped %d records with extreme past timestamps in column %s", past_count, col)

    return df_cleaned


def remove_invalid_records(df: pd.DataFrame, required_cols: List[str]) -> pd.DataFrame:
    """
    Drops rows where essential columns are null, empty, or whitespace.
    """
    df_cleaned = df.copy()
    initial_len = len(df_cleaned)

    for col in required_cols:
        if col not in df_cleaned.columns:
            continue
        
        # Handle string column empty space checks
        if pd.api.types.is_string_dtype(df_cleaned[col]):
            empty_str_mask = df_cleaned[col].astype(str).str.strip() == ""
            df_cleaned = df_cleaned[~empty_str_mask]

        df_cleaned = df_cleaned.dropna(subset=[col])

    removed_count = initial_len - len(df_cleaned)
    if removed_count > 0:
        logger.info("Dropped %d invalid records lacking required columns: %s", removed_count, required_cols)

    return df_cleaned


def handle_null_occupancy(
    df: pd.DataFrame,
    occupied_col: str = "occupied_slots",
    total_col: str = "total_slots",
    percentage_col: str = "occupancy_percentage",
) -> pd.DataFrame:
    """
    Cleans occupancy specific metrics, recalculating occupancy percentage or slots where missing or mismatched.
    Drops any rows where total slots are <= 0.
    """
    df_cleaned = df.copy()

    # Drop non-positive total slots
    if total_col in df_cleaned.columns:
        invalid_total_mask = df_cleaned[total_col] <= 0
        invalid_total_count = invalid_total_mask.sum()
        if invalid_total_count > 0:
            df_cleaned = df_cleaned[~invalid_total_mask]
            logger.info("Dropped %d records with total_slots <= 0", invalid_total_count)

    if len(df_cleaned) == 0:
        return df_cleaned

    # Handle null occupied slots by setting them to 0 or calculating if percentage is present
    if occupied_col in df_cleaned.columns:
        if total_col in df_cleaned.columns and percentage_col in df_cleaned.columns:
            calc_occupied = (df_cleaned[percentage_col] / 100.0 * df_cleaned[total_col]).round().astype(int)
            df_cleaned[occupied_col] = df_cleaned[occupied_col].fillna(calc_occupied)
        df_cleaned[occupied_col] = df_cleaned[occupied_col].fillna(0).clip(lower=0)

    # Ensure occupied_slots does not exceed total_slots
    if occupied_col in df_cleaned.columns and total_col in df_cleaned.columns:
        over_limit_mask = df_cleaned[occupied_col] > df_cleaned[total_col]
        if over_limit_mask.any():
            logger.warning("Clamping occupied_slots to total_slots in %d records", over_limit_mask.sum())
            df_cleaned.loc[over_limit_mask, occupied_col] = df_cleaned.loc[over_limit_mask, total_col]

    # Re-calculate occupancy_percentage and available_slots
    if total_col in df_cleaned.columns and occupied_col in df_cleaned.columns:
        df_cleaned[percentage_col] = (df_cleaned[occupied_col] / df_cleaned[total_col] * 100.0).round(4)
        if "available_slots" in df_cleaned.columns:
            df_cleaned["available_slots"] = df_cleaned[total_col] - df_cleaned[occupied_col]

    return df_cleaned


def handle_invalid_reservation_durations(
    df: pd.DataFrame,
    start_col: str = "reservation_start",
    end_col: str = "reservation_end",
    duration_col: str = "duration_minutes",
) -> pd.DataFrame:
    """
    Cleans reservation records by ensuring valid timestamps and computing missing/negative durations.
    """
    df_cleaned = df.copy()

    # Ensure start is before end
    if start_col in df_cleaned.columns and end_col in df_cleaned.columns:
        invalid_time_mask = df_cleaned[start_col] > df_cleaned[end_col]
        invalid_time_count = invalid_time_mask.sum()
        if invalid_time_count > 0:
            df_cleaned = df_cleaned[~invalid_time_mask]
            logger.info("Dropped %d reservations where start_time > end_time", invalid_time_count)

    if len(df_cleaned) == 0:
        return df_cleaned

    # Calculate duration if duration is null or negative/zero
    if start_col in df_cleaned.columns and end_col in df_cleaned.columns and duration_col in df_cleaned.columns:
        calculated_duration = (df_cleaned[end_col] - df_cleaned[start_col]).dt.total_seconds() / 60.0
        calculated_duration = calculated_duration.clip(lower=0.0)

        invalid_duration_mask = (df_cleaned[duration_col].isna()) | (df_cleaned[duration_col] <= 0)
        invalid_duration_count = invalid_duration_mask.sum()
        if invalid_duration_count > 0:
            df_cleaned.loc[invalid_duration_mask, duration_col] = calculated_duration.loc[invalid_duration_mask]
            logger.info("Fixed invalid/missing duration_minutes for %d reservations", invalid_duration_count)

    return df_cleaned


def handle_invalid_parking_sessions(
    df: pd.DataFrame,
    check_in_col: str = "check_in_time",
    check_out_col: str = "check_out_time",
    duration_col: str = "duration_minutes",
    fee_col: str = "parking_fee",
) -> pd.DataFrame:
    """
    Cleans parking session records by validating check-in/check-out chronology, duration, and fee.
    """
    df_cleaned = df.copy()

    # If checkout exists, check chronological order
    if check_in_col in df_cleaned.columns and check_out_col in df_cleaned.columns:
        checkout_present = df_cleaned[check_out_col].notna()
        invalid_sequence = checkout_present & (df_cleaned[check_in_col] > df_cleaned[check_out_col])
        invalid_count = invalid_sequence.sum()
        if invalid_count > 0:
            df_cleaned = df_cleaned[~invalid_sequence]
            logger.info("Dropped %d sessions with check_in_time > check_out_time", invalid_count)

    if len(df_cleaned) == 0:
        return df_cleaned

    # If duration is missing but check out is present, compute it
    if check_in_col in df_cleaned.columns and check_out_col in df_cleaned.columns and duration_col in df_cleaned.columns:
        calculated_duration = (df_cleaned[check_out_col] - df_cleaned[check_in_col]).dt.total_seconds() / 60.0
        calculated_duration = calculated_duration.clip(lower=0.0)

        invalid_duration = df_cleaned[check_out_col].notna() & (
            df_cleaned[duration_col].isna() | (df_cleaned[duration_col] <= 0)
        )
        if invalid_duration.any():
            df_cleaned.loc[invalid_duration, duration_col] = calculated_duration.loc[invalid_duration]
            logger.info("Recomputed duration_minutes for %d completed sessions", invalid_duration.sum())

    # Set duration to NaN if check out is not present (active sessions)
    if check_out_col in df_cleaned.columns and duration_col in df_cleaned.columns:
        active_sessions = df_cleaned[check_out_col].isna()
        df_cleaned.loc[active_sessions, duration_col] = np.nan

    # Validate parking fee (must be >= 0 or default to 0.0)
    if fee_col in df_cleaned.columns:
        # Default active sessions fee to NaN or 0
        active_sessions = df_cleaned[check_out_col].isna() if check_out_col in df_cleaned.columns else pd.Series(False, index=df_cleaned.index)
        df_cleaned.loc[active_sessions, fee_col] = np.nan
        
        # Non-negative fees for completed sessions
        completed_sessions = ~active_sessions
        negative_fees = completed_sessions & (df_cleaned[fee_col] < 0)
        if negative_fees.any():
            logger.warning("Reset negative parking fees to 0.0 for %d sessions", negative_fees.sum())
            df_cleaned.loc[negative_fees, fee_col] = 0.0

    return df_cleaned


def detect_outliers(
    df: pd.DataFrame,
    columns: List[str],
    method: str = "iqr",
    threshold: float = 1.5,
) -> pd.Series:
    """
    Detects outliers in the specified columns of the DataFrame.
    Returns a Boolean Series where True indicates that the row contains an outlier.
    """
    outlier_mask = pd.Series(False, index=df.index)

    for col in columns:
        if col not in df.columns or not pd.api.types.is_numeric_dtype(df[col]):
            continue

        non_null_col = df[col].dropna()
        if len(non_null_col) == 0:
            continue

        if method == "iqr":
            q1 = non_null_col.quantile(0.25)
            q3 = non_null_col.quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - threshold * iqr
            upper_bound = q3 + threshold * iqr
            col_outliers = (df[col] < lower_bound) | (df[col] > upper_bound)
            outlier_mask = outlier_mask | col_outliers
        elif method == "zscore":
            mean_val = non_null_col.mean()
            std_val = non_null_col.std()
            if std_val > 0:
                z_scores = (df[col] - mean_val) / std_val
                col_outliers = z_scores.abs() > threshold
                outlier_mask = outlier_mask | col_outliers

    return outlier_mask


def remove_outliers(
    df: pd.DataFrame,
    columns: List[str],
    method: str = "iqr",
    threshold: float = 1.5,
) -> pd.DataFrame:
    """
    Removes outliers from the DataFrame.
    """
    outlier_mask = detect_outliers(df, columns, method=method, threshold=threshold)
    outlier_count = outlier_mask.sum()
    if outlier_count > 0:
        df_cleaned = df[~outlier_mask]
        logger.info("Removed %d outliers using %s method from columns: %s", outlier_count, method, columns)
        return df_cleaned
    return df
