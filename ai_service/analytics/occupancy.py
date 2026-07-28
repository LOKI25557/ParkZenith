"""
Occupancy analytics calculations using Pandas.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
from ai_service.analytics.statistics import safe_mean, safe_max, safe_min


def calculate_current_occupancy(df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """
    Retrieves the most recent occupancy metrics from the DataFrame.
    """
    if df.empty:
        return None

    # Get the row with the maximum collected_at timestamp
    latest_row = df.loc[df["collected_at"].idxmax()]
    
    # Handle timestamp serialization
    collected_at_val = latest_row["collected_at"]
    if isinstance(collected_at_val, pd.Timestamp):
        collected_at_str = collected_at_val.isoformat()
    else:
        collected_at_str = str(collected_at_val)

    return {
        "facility_id": str(latest_row["facility_id"]),
        "zone_id": str(latest_row["zone_id"]) if pd.notna(latest_row.get("zone_id")) else None,
        "occupied_slots": int(latest_row["occupied_slots"]),
        "available_slots": int(latest_row["available_slots"]),
        "total_slots": int(latest_row["total_slots"]),
        "occupancy_percentage": float(round(latest_row["occupancy_percentage"], 2)),
        "collected_at": collected_at_str,
    }


def calculate_occupancy_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculates summary occupancy metrics: average, max, min, and percentage.
    """
    if df.empty:
        return {
            "average_occupancy": 0.0,
            "maximum_occupancy": 0.0,
            "minimum_occupancy": 0.0,
            "occupancy_percentage": 0.0,
        }

    avg_occ = safe_mean(df["occupied_slots"])
    max_occ = safe_max(df["occupied_slots"])
    min_occ = safe_min(df["occupied_slots"])
    avg_percentage = safe_mean(df["occupancy_percentage"])

    return {
        "average_occupancy": avg_occ,
        "maximum_occupancy": max_occ,
        "minimum_occupancy": min_occ,
        "occupancy_percentage": avg_percentage,
    }


def calculate_hourly_trend(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Calculates the average occupancy percentage grouped by hour of the day (0-23).
    """
    if df.empty:
        return []
    
    df_copy = df.copy()
    df_copy["hour"] = df_copy["collected_at"].dt.hour
    hourly_mean = df_copy.groupby("hour")["occupancy_percentage"].mean().round(2)
    
    # Ensure all 24 hours are represented, filled with 0.0 if missing
    trend = []
    for h in range(24):
        trend.append({
            "hour": h,
            "occupancy_percentage": float(hourly_mean.get(h, 0.0))
        })
    return trend


def calculate_daily_trend(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Calculates the average occupancy percentage grouped by day of the week (0=Monday, 6=Sunday).
    """
    if df.empty:
        return []
    
    df_copy = df.copy()
    df_copy["day_of_week"] = df_copy["collected_at"].dt.dayofweek
    daily_mean = df_copy.groupby("day_of_week")["occupancy_percentage"].mean().round(2)
    
    days_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    trend = []
    for d in range(7):
        trend.append({
            "day_of_week": d,
            "day_name": days_names[d],
            "occupancy_percentage": float(daily_mean.get(d, 0.0))
        })
    return trend


def calculate_weekly_trend(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Calculates the average occupancy percentage grouped by calendar week.
    """
    if df.empty:
        return []
    
    df_copy = df.copy()
    df_copy["week"] = df_copy["collected_at"].dt.isocalendar().week
    weekly_mean = df_copy.groupby("week")["occupancy_percentage"].mean().round(2)
    
    trend = []
    for week, val in weekly_mean.items():
        trend.append({
            "week": int(week),
            "occupancy_percentage": float(val)
        })
    return trend


def calculate_monthly_trend(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Calculates the average occupancy percentage grouped by month (1-12).
    """
    if df.empty:
        return []
    
    df_copy = df.copy()
    df_copy["month"] = df_copy["collected_at"].dt.month
    monthly_mean = df_copy.groupby("month")["occupancy_percentage"].mean().round(2)
    
    months_names = [
        "", "January", "February", "March", "April", "May", "June", 
        "July", "August", "September", "October", "November", "December"
    ]
    trend = []
    for m in range(1, 13):
        if m in monthly_mean:
            trend.append({
                "month": m,
                "month_name": months_names[m],
                "occupancy_percentage": float(monthly_mean.get(m, 0.0))
            })
    return trend


def detect_peak_hours(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Determines peak occupancy hours, least busy hours, busiest day, and least busy day.
    """
    if df.empty:
        return {
            "peak_hours": [],
            "least_busy_hours": [],
            "busiest_day": None,
            "least_busy_day": None,
            "average_occupancy_by_hour": [],
        }

    df_copy = df.copy()
    df_copy["hour"] = df_copy["collected_at"].dt.hour
    df_copy["day_of_week"] = df_copy["collected_at"].dt.dayofweek
    
    # Calculate hourly average occupancy
    hourly_stats = df_copy.groupby("hour")["occupancy_percentage"].mean().round(2)
    hourly_stats_list = [
        {"hour": int(h), "occupancy_percentage": float(val)}
        for h, val in hourly_stats.items()
    ]
    
    # Rank hours by occupancy
    sorted_hours = sorted(hourly_stats_list, key=lambda x: x["occupancy_percentage"], reverse=True)
    peak_hours = [f"{h['hour']:02d}:00" for h in sorted_hours[:5]]
    least_busy_hours = [f"{h['hour']:02d}:00" for h in reversed(sorted_hours[-5:])]
    
    # Rank days by occupancy
    daily_stats = df_copy.groupby("day_of_week")["occupancy_percentage"].mean().round(2)
    days_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    busiest_day_idx = daily_stats.idxmax() if not daily_stats.empty else None
    least_busy_day_idx = daily_stats.idxmin() if not daily_stats.empty else None
    
    return {
        "peak_hours": peak_hours,
        "least_busy_hours": least_busy_hours,
        "busiest_day": days_names[busiest_day_idx] if busiest_day_idx is not None else None,
        "least_busy_day": days_names[least_busy_day_idx] if least_busy_day_idx is not None else None,
        "average_occupancy_by_hour": sorted(hourly_stats_list, key=lambda x: x["hour"]),
    }
