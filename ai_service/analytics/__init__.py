"""
Analytics package initialization.
"""

from ai_service.analytics.occupancy import (
    calculate_current_occupancy,
    calculate_occupancy_metrics,
    calculate_hourly_trend,
    calculate_daily_trend,
    calculate_weekly_trend,
    calculate_monthly_trend,
    detect_peak_hours,
)
from ai_service.analytics.utilization import calculate_utilization_metrics
from ai_service.analytics.reservation import calculate_reservation_metrics
from ai_service.analytics.sessions import calculate_session_metrics
from ai_service.analytics.trends import calculate_occupancy_rolling_average
from ai_service.analytics.reports import (
    generate_daily_report,
    generate_weekly_report,
    generate_monthly_report,
    generate_summary_report,
)

__all__ = [
    "calculate_current_occupancy",
    "calculate_occupancy_metrics",
    "calculate_hourly_trend",
    "calculate_daily_trend",
    "calculate_weekly_trend",
    "calculate_monthly_trend",
    "detect_peak_hours",
    "calculate_utilization_metrics",
    "calculate_reservation_metrics",
    "calculate_session_metrics",
    "calculate_occupancy_rolling_average",
    "generate_daily_report",
    "generate_weekly_report",
    "generate_monthly_report",
    "generate_summary_report",
]
