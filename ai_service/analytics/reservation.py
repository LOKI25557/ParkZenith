"""
Reservation analytics calculations using Pandas.
"""

from typing import Dict, Any, List
import pandas as pd
from ai_service.analytics.statistics import safe_mean


def calculate_reservation_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes total reservations, success rate, cancellation rate, and durations.
    """
    if df.empty:
        return {
            "total_reservations": 0,
            "reservations_per_facility": {},
            "reservations_per_day": {},
            "reservation_success_rate": 0.0,
            "cancellation_rate": 0.0,
            "average_reservation_duration": 0.0,
            "reservation_trend": [],
        }

    total_res = len(df)

    # Success / cancellation rates
    status_counts = df["reservation_status"].str.upper().value_counts()
    completed_count = status_counts.get("COMPLETED", 0)
    cancelled_count = status_counts.get("CANCELLED", 0)

    success_rate = float(round((completed_count / total_res * 100.0), 2)) if total_res > 0 else 0.0
    cancellation_rate = float(round((cancelled_count / total_res * 100.0), 2)) if total_res > 0 else 0.0

    # Average reservation duration
    avg_duration = safe_mean(df["duration_minutes"])

    # Reservations per facility
    facility_counts = df["facility_id"].value_counts()
    res_per_facility = {str(fac): int(cnt) for fac, cnt in facility_counts.items()}

    # Reservations per day (by reservation_start date)
    df_copy = df.copy()
    df_copy["reservation_start"] = pd.to_datetime(df_copy["reservation_start"])
    df_copy["date"] = df_copy["reservation_start"].dt.date
    day_counts = df_copy["date"].value_counts().sort_index()
    res_per_day = {str(date): int(cnt) for date, cnt in day_counts.items()}

    # Reservation trends by date
    trend = []
    for date, cnt in day_counts.items():
        trend.append({
            "date": str(date),
            "reservations_count": int(cnt)
        })

    return {
        "total_reservations": total_res,
        "reservations_per_facility": res_per_facility,
        "reservations_per_day": res_per_day,
        "reservation_success_rate": success_rate,
        "cancellation_rate": cancellation_rate,
        "average_reservation_duration": avg_duration,
        "reservation_trend": trend,
    }
