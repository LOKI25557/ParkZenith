"""
Report builders for generating structured daily, weekly, monthly, and summary reports.
"""

from typing import Dict, Any
import pandas as pd

from ai_service.analytics.occupancy import (
    calculate_occupancy_metrics,
    calculate_current_occupancy,
    calculate_hourly_trend,
    detect_peak_hours,
)
from ai_service.analytics.utilization import calculate_utilization_metrics
from ai_service.analytics.reservation import calculate_reservation_metrics
from ai_service.analytics.sessions import calculate_session_metrics


def generate_daily_report(
    occupancy_df: pd.DataFrame,
    reservation_df: pd.DataFrame,
    session_df: pd.DataFrame,
    date_str: str,
) -> Dict[str, Any]:
    """
    Generates a daily report for a specified date string (YYYY-MM-DD).
    """
    occ_metrics = calculate_occupancy_metrics(occupancy_df)
    util_metrics = calculate_utilization_metrics(occupancy_df)
    res_metrics = calculate_reservation_metrics(reservation_df)
    sess_metrics = calculate_session_metrics(session_df)
    peak_metrics = detect_peak_hours(occupancy_df)
    current_occ = calculate_current_occupancy(occupancy_df)

    return {
        "report_type": "DAILY",
        "date": date_str,
        "occupancy": {
            "current": current_occ,
            "average_slots_occupied": util_metrics["average_occupied_slots"],
            "average_slots_available": util_metrics["average_available_slots"],
            "maximum_occupancy": occ_metrics["maximum_occupancy"],
            "minimum_occupancy": occ_metrics["minimum_occupancy"],
            "average_occupancy_percentage": occ_metrics["occupancy_percentage"],
        },
        "utilization": {
            "facility_utilization": util_metrics["facility_utilization"],
            "zone_utilization": util_metrics["zone_utilization"],
            "slot_utilization": util_metrics["slot_utilization"],
            "efficiency": util_metrics["occupancy_efficiency"],
        },
        "reservations": {
            "total_reservations": res_metrics["total_reservations"],
            "success_rate": res_metrics["reservation_success_rate"],
            "cancellation_rate": res_metrics["cancellation_rate"],
            "average_duration_minutes": res_metrics["average_reservation_duration"],
        },
        "sessions": {
            "session_count": sess_metrics["session_count"],
            "average_duration_minutes": sess_metrics["average_duration"],
            "median_duration_minutes": sess_metrics["median_duration"],
            "duration_distribution": sess_metrics["duration_distribution"],
        },
        "traffic": {
            "peak_hours": peak_metrics["peak_hours"],
            "least_busy_hours": peak_metrics["least_busy_hours"],
        },
    }


def generate_weekly_report(
    occupancy_df: pd.DataFrame,
    reservation_df: pd.DataFrame,
    session_df: pd.DataFrame,
    start_date_str: str,
    end_date_str: str,
) -> Dict[str, Any]:
    """
    Generates a weekly report covering the specified range.
    """
    occ_metrics = calculate_occupancy_metrics(occupancy_df)
    util_metrics = calculate_utilization_metrics(occupancy_df)
    res_metrics = calculate_reservation_metrics(reservation_df)
    sess_metrics = calculate_session_metrics(session_df)
    peak_metrics = detect_peak_hours(occupancy_df)

    return {
        "report_type": "WEEKLY",
        "date_range": {
            "start": start_date_str,
            "end": end_date_str,
        },
        "occupancy": {
            "average_slots_occupied": util_metrics["average_occupied_slots"],
            "average_slots_available": util_metrics["average_available_slots"],
            "maximum_occupancy": occ_metrics["maximum_occupancy"],
            "minimum_occupancy": occ_metrics["minimum_occupancy"],
            "average_occupancy_percentage": occ_metrics["occupancy_percentage"],
        },
        "utilization": {
            "facility_utilization": util_metrics["facility_utilization"],
            "zone_utilization": util_metrics["zone_utilization"],
            "slot_utilization": util_metrics["slot_utilization"],
            "efficiency": util_metrics["occupancy_efficiency"],
        },
        "reservations": {
            "total_reservations": res_metrics["total_reservations"],
            "success_rate": res_metrics["reservation_success_rate"],
            "cancellation_rate": res_metrics["cancellation_rate"],
            "average_duration_minutes": res_metrics["average_reservation_duration"],
        },
        "sessions": {
            "session_count": sess_metrics["session_count"],
            "average_duration_minutes": sess_metrics["average_duration"],
            "median_duration_minutes": sess_metrics["median_duration"],
            "duration_distribution": sess_metrics["duration_distribution"],
        },
        "traffic": {
            "peak_hours": peak_metrics["peak_hours"],
            "least_busy_hours": peak_metrics["least_busy_hours"],
            "busiest_day": peak_metrics["busiest_day"],
            "least_busy_day": peak_metrics["least_busy_day"],
        },
    }


def generate_monthly_report(
    occupancy_df: pd.DataFrame,
    reservation_df: pd.DataFrame,
    session_df: pd.DataFrame,
    year: int,
    month: int,
) -> Dict[str, Any]:
    """
    Generates a monthly report for the specified year and month.
    """
    occ_metrics = calculate_occupancy_metrics(occupancy_df)
    util_metrics = calculate_utilization_metrics(occupancy_df)
    res_metrics = calculate_reservation_metrics(reservation_df)
    sess_metrics = calculate_session_metrics(session_df)
    peak_metrics = detect_peak_hours(occupancy_df)

    return {
        "report_type": "MONTHLY",
        "period": f"{year:04d}-{month:02d}",
        "occupancy": {
            "average_slots_occupied": util_metrics["average_occupied_slots"],
            "average_slots_available": util_metrics["average_available_slots"],
            "maximum_occupancy": occ_metrics["maximum_occupancy"],
            "minimum_occupancy": occ_metrics["minimum_occupancy"],
            "average_occupancy_percentage": occ_metrics["occupancy_percentage"],
        },
        "utilization": {
            "facility_utilization": util_metrics["facility_utilization"],
            "zone_utilization": util_metrics["zone_utilization"],
            "slot_utilization": util_metrics["slot_utilization"],
            "efficiency": util_metrics["occupancy_efficiency"],
        },
        "reservations": {
            "total_reservations": res_metrics["total_reservations"],
            "success_rate": res_metrics["reservation_success_rate"],
            "cancellation_rate": res_metrics["cancellation_rate"],
            "average_duration_minutes": res_metrics["average_reservation_duration"],
        },
        "sessions": {
            "session_count": sess_metrics["session_count"],
            "average_duration_minutes": sess_metrics["average_duration"],
            "median_duration_minutes": sess_metrics["median_duration"],
            "duration_distribution": sess_metrics["duration_distribution"],
        },
        "traffic": {
            "peak_hours": peak_metrics["peak_hours"],
            "least_busy_hours": peak_metrics["least_busy_hours"],
            "busiest_day": peak_metrics["busiest_day"],
            "least_busy_day": peak_metrics["least_busy_day"],
        },
    }


def generate_summary_report(
    occupancy_df: pd.DataFrame,
    reservation_df: pd.DataFrame,
    session_df: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Generates a high-level summary report for a overall time frame.
    """
    occ_metrics = calculate_occupancy_metrics(occupancy_df)
    util_metrics = calculate_utilization_metrics(occupancy_df)
    res_metrics = calculate_reservation_metrics(reservation_df)
    sess_metrics = calculate_session_metrics(session_df)
    peak_metrics = detect_peak_hours(occupancy_df)

    return {
        "report_type": "SUMMARY",
        "occupancy": {
            "average_slots_occupied": util_metrics["average_occupied_slots"],
            "average_slots_available": util_metrics["average_available_slots"],
            "maximum_occupancy": occ_metrics["maximum_occupancy"],
            "minimum_occupancy": occ_metrics["minimum_occupancy"],
            "average_occupancy_percentage": occ_metrics["occupancy_percentage"],
        },
        "utilization": {
            "facility_utilization": util_metrics["facility_utilization"],
            "zone_utilization": util_metrics["zone_utilization"],
            "slot_utilization": util_metrics["slot_utilization"],
            "efficiency": util_metrics["occupancy_efficiency"],
        },
        "reservations": {
            "total_reservations": res_metrics["total_reservations"],
            "success_rate": res_metrics["reservation_success_rate"],
            "cancellation_rate": res_metrics["cancellation_rate"],
            "average_duration_minutes": res_metrics["average_reservation_duration"],
        },
        "sessions": {
            "session_count": sess_metrics["session_count"],
            "average_duration_minutes": sess_metrics["average_duration"],
            "median_duration_minutes": sess_metrics["median_duration"],
            "duration_distribution": sess_metrics["duration_distribution"],
        },
        "traffic": {
            "peak_hours": peak_metrics["peak_hours"],
            "least_busy_hours": peak_metrics["least_busy_hours"],
            "busiest_day": peak_metrics["busiest_day"],
            "least_busy_day": peak_metrics["least_busy_day"],
        },
    }
