"""
Parking session analytics calculations using Pandas.
"""

from typing import Dict, Any
import pandas as pd
from ai_service.analytics.statistics import (
    safe_mean,
    safe_median,
    safe_min,
    safe_max,
    calculate_distribution,
)


def calculate_session_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes parking session counts, duration stats, and distributions.
    """
    if df.empty:
        return {
            "session_count": 0,
            "sessions_per_facility": {},
            "sessions_per_day": {},
            "average_duration": 0.0,
            "median_duration": 0.0,
            "minimum_duration": 0.0,
            "maximum_duration": 0.0,
            "duration_distribution": {
                "<30m": 0,
                "30m-1h": 0,
                "1h-2h": 0,
                "2h-4h": 0,
                "4h+": 0,
            },
        }

    session_cnt = len(df)

    # Calculate duration stats (excluding active/unfinished sessions with null duration_minutes)
    valid_durations = df["duration_minutes"].dropna()

    avg_duration = safe_mean(valid_durations)
    med_duration = safe_median(valid_durations)
    min_duration = safe_min(valid_durations)
    max_duration = safe_max(valid_durations)

    # Duration distribution
    bins = [0.0, 30.0, 60.0, 120.0, 240.0, float("inf")]
    labels = ["<30m", "30m-1h", "1h-2h", "2h-4h", "4h+"]
    duration_dist = calculate_distribution(valid_durations, bins, labels)

    # Sessions per facility
    facility_counts = df["facility_id"].value_counts()
    sess_per_facility = {str(fac): int(cnt) for fac, cnt in facility_counts.items()}

    # Sessions per day (by check_in_time date)
    df_copy = df.copy()
    df_copy["check_in_time"] = pd.to_datetime(df_copy["check_in_time"])
    df_copy["date"] = df_copy["check_in_time"].dt.date
    day_counts = df_copy["date"].value_counts().sort_index()
    sess_per_day = {str(date): int(cnt) for date, cnt in day_counts.items()}

    return {
        "session_count": session_cnt,
        "sessions_per_facility": sess_per_facility,
        "sessions_per_day": sess_per_day,
        "average_duration": avg_duration,
        "median_duration": med_duration,
        "minimum_duration": min_duration,
        "maximum_duration": max_duration,
        "duration_distribution": duration_dist,
    }
