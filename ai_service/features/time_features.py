"""
Time Features module for ParkZenith Feature Engineering.
Extracts calendar and business/peak indicators from datetime columns.
"""

import logging
import pandas as pd
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)


def is_us_holiday(dt_series: pd.Series) -> pd.Series:
    """
    Computes a basic holiday flag (1 if standard holiday, 0 otherwise) using date arithmetic.
    Avoids external library dependencies.
    Covers:
      - New Year's Day (Jan 1)
      - Independence Day (Jul 4)
      - Veteran's Day (Nov 11)
      - Christmas Day (Dec 25)
      - Memorial Day (Last Monday of May)
      - Labor Day (First Monday of Sep)
      - Thanksgiving (Fourth Thursday of Nov)
    """
    months = dt_series.dt.month
    days = dt_series.dt.day
    dayofweek = dt_series.dt.dayofweek  # 0=Monday, 6=Sunday

    # Fixed date holidays
    is_jan1 = (months == 1) & (days == 1)
    is_jul4 = (months == 7) & (days == 4)
    is_nov11 = (months == 11) & (days == 11)
    is_dec25 = (months == 12) & (days == 25)

    # Dynamic date holidays
    # Memorial Day (Last Monday of May): Month is 5, dayofweek is 0, and day is between 25 and 31
    is_memorial = (months == 5) & (dayofweek == 0) & (days >= 25)

    # Labor Day (First Monday of September): Month is 9, dayofweek is 0, and day is between 1 and 7
    is_labor = (months == 9) & (dayofweek == 0) & (days <= 7)

    # Thanksgiving Day (Fourth Thursday of November): Month is 11, dayofweek is 3 (Thursday), and day is between 22 and 28
    is_thanksgiving = (months == 11) & (dayofweek == 3) & (days >= 22) & (days <= 28)

    holiday_mask = (
        is_jan1 | is_jul4 | is_nov11 | is_dec25 | is_memorial | is_labor | is_thanksgiving
    )
    return holiday_mask.astype(int)


def generate_time_features(
    df: pd.DataFrame,
    timestamp_col: str,
    prefix: str = "time_",
    group_cols: Optional[list] = None,
) -> pd.DataFrame:
    """
    Generates time features: hour, day of week, week number, month, quarter,
    weekend flag, business hour flag, peak hour flag, holiday flag, and time since previous update.
    """
    df_feat = df.copy()
    
    if timestamp_col not in df_feat.columns:
        logger.warning("Timestamp column '%s' not found. Skipping time feature generation.", timestamp_col)
        return df_feat

    dt = pd.to_datetime(df_feat[timestamp_col])

    # Basic datetime components
    df_feat[f"{prefix}hour"] = dt.dt.hour
    df_feat[f"{prefix}dayofweek"] = dt.dt.dayofweek
    df_feat[f"{prefix}week"] = dt.dt.isocalendar().week.astype(int)
    df_feat[f"{prefix}month"] = dt.dt.month
    df_feat[f"{prefix}quarter"] = dt.dt.quarter

    # Flags
    df_feat[f"{prefix}is_weekend"] = (dt.dt.dayofweek >= 5).astype(int)
    
    # Business hours: 08:00 - 18:00 on weekdays (Mon-Fri)
    df_feat[f"{prefix}is_business_hour"] = (
        (dt.dt.hour >= 8) & (dt.dt.hour < 18) & (dt.dt.dayofweek < 5)
    ).astype(int)

    # Peak hours: typically commute & lunchtime peaks (e.g. 8-10, 12-14, 16-18)
    df_feat[f"{prefix}is_peak_hour"] = (
        dt.dt.hour.isin([8, 9, 12, 13, 16, 17])
    ).astype(int)

    # Holidays
    df_feat[f"{prefix}is_holiday"] = is_us_holiday(dt)

    # Time since previous update (in seconds)
    # Grouping is important to avoid diffing between different facilities
    if group_cols:
        # Sort values first to make sure diff is correct
        df_feat = df_feat.sort_values(by=group_cols + [timestamp_col])
        df_feat[f"{prefix}since_last_update"] = (
            df_feat.groupby(group_cols)[timestamp_col]
            .diff()
            .dt.total_seconds()
            .fillna(0.0)
        )
    else:
        df_feat = df_feat.sort_values(by=[timestamp_col])
        df_feat[f"{prefix}since_last_update"] = (
            dt.diff().dt.total_seconds().fillna(0.0)
        )

    logger.info("Generated time features from column: %s", timestamp_col)
    return df_feat
