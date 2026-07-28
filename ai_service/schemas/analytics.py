"""
Pydantic schemas for the Analytics Engine response models.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class CurrentOccupancySchema(BaseModel):
    """Schema representing current occupancy details."""
    facility_id: str = Field(..., description="Facility Identifier")
    zone_id: Optional[str] = Field(None, description="Zone Identifier")
    occupied_slots: int = Field(..., description="Number of currently occupied slots")
    available_slots: int = Field(..., description="Number of currently available slots")
    total_slots: int = Field(..., description="Total slots capacity")
    occupancy_percentage: float = Field(..., description="Occupancy percentage")
    collected_at: str = Field(..., description="Timestamp when data was collected")


class OverviewResponse(BaseModel):
    """Dashboard-friendly high-level summary response schema."""
    facility_id: Optional[str] = Field(None, description="Filtered facility identifier, if any")
    current_occupancy: Optional[CurrentOccupancySchema] = Field(None, description="Latest collected occupancy snapshot")
    average_occupancy: float = Field(..., description="Average occupied slots over duration")
    facility_utilization: float = Field(..., description="Average occupancy percentage over duration")
    peak_hour: Optional[str] = Field(None, description="Busiest hour of the day (e.g. 18:00)")
    least_busy_hour: Optional[str] = Field(None, description="Least busy hour of the day (e.g. 09:00)")
    average_session_duration: float = Field(..., description="Average session duration in minutes")
    reservation_count: int = Field(..., description="Total number of reservations in range")
    today_sessions: int = Field(..., description="Number of sessions check-in today")
    today_reservations: int = Field(..., description="Number of reservations scheduled today")


class OccupancyAnalyticsResponse(BaseModel):
    """Detailed occupancy statistics response schema."""
    average_occupancy: float = Field(..., description="Average occupied slots")
    maximum_occupancy: float = Field(..., description="Maximum occupied slots")
    minimum_occupancy: float = Field(..., description="Minimum occupied slots")
    occupancy_percentage: float = Field(..., description="Average occupancy percentage")
    hourly_trend: List[Dict[str, Any]] = Field(..., description="Occupancy percentage by hour")
    daily_trend: List[Dict[str, Any]] = Field(..., description="Occupancy percentage by day of week")
    weekly_trend: List[Dict[str, Any]] = Field(..., description="Occupancy percentage by calendar week")
    monthly_trend: List[Dict[str, Any]] = Field(..., description="Occupancy percentage by month")


class UtilizationAnalyticsResponse(BaseModel):
    """Detailed utilization metrics response schema."""
    facility_utilization: float = Field(..., description="Overall occupancy percentage")
    zone_utilization: Dict[str, float] = Field(..., description="Occupancy percentage grouped by zone")
    slot_utilization: float = Field(..., description="Ratio of average occupied slots to total slots")
    occupancy_efficiency: float = Field(..., description="Occupancy efficiency ratio")
    average_available_slots: float = Field(..., description="Average available slots count")
    average_occupied_slots: float = Field(..., description="Average occupied slots count")


class ReservationAnalyticsResponse(BaseModel):
    """Detailed reservation metrics response schema."""
    total_reservations: int = Field(..., description="Total reservation bookings")
    reservations_per_facility: Dict[str, int] = Field(..., description="Reservation counts per facility")
    reservations_per_day: Dict[str, int] = Field(..., description="Daily counts of reservations")
    reservation_success_rate: float = Field(..., description="Percentage of COMPLETED reservations")
    cancellation_rate: float = Field(..., description="Percentage of CANCELLED reservations")
    average_reservation_duration: float = Field(..., description="Average booking duration in minutes")
    reservation_trend: List[Dict[str, Any]] = Field(..., description="Daily reservation trends")


class SessionAnalyticsResponse(BaseModel):
    """Detailed parking session metrics response schema."""
    session_count: int = Field(..., description="Total check-in sessions")
    sessions_per_facility: Dict[str, int] = Field(..., description="Session counts per facility")
    sessions_per_day: Dict[str, int] = Field(..., description="Daily check-in session counts")
    average_duration: float = Field(..., description="Average parking duration in minutes")
    median_duration: float = Field(..., description="Median parking duration in minutes")
    minimum_duration: float = Field(..., description="Minimum parking duration in minutes")
    maximum_duration: float = Field(..., description="Maximum parking duration in minutes")
    duration_distribution: Dict[str, int] = Field(..., description="Frequency distribution count by duration buckets")


class PeakHoursResponse(BaseModel):
    """Peak and off-peak hour metrics response schema."""
    peak_hours: List[str] = Field(..., description="Ranked peak busy hours (HH:00)")
    least_busy_hours: List[str] = Field(..., description="Ranked least busy hours (HH:00)")
    busiest_day: Optional[str] = Field(None, description="Name of busiest day of the week")
    least_busy_day: Optional[str] = Field(None, description="Name of least busy day of the week")
    average_occupancy_by_hour: List[Dict[str, Any]] = Field(..., description="Average occupancy by hour of the day")


class TrendsResponse(BaseModel):
    """Time-series trends and rolling average response schema."""
    rolling_average: List[Dict[str, Any]] = Field(..., description="Occupancy percentage rolling averages")
    hourly_trend: List[Dict[str, Any]] = Field(..., description="Hourly trend details")
    daily_trend: List[Dict[str, Any]] = Field(..., description="Daily trend details")
    weekly_trend: List[Dict[str, Any]] = Field(..., description="Weekly trend details")
    monthly_trend: List[Dict[str, Any]] = Field(..., description="Monthly trend details")


class ReportResponse(BaseModel):
    """Generic structured JSON report response schema."""
    report_type: str = Field(..., description="DAILY, WEEKLY, MONTHLY, or SUMMARY")
    period_info: Optional[str] = Field(None, alias="period", description="Specific day, week, month or summary context")
    date_range: Optional[Dict[str, str]] = Field(None, description="Date range covered")
    occupancy: Dict[str, Any] = Field(..., description="Occupancy key performance indicators")
    utilization: Dict[str, Any] = Field(..., description="Space utilization indicators")
    reservations: Dict[str, Any] = Field(..., description="Reservation KPIs")
    sessions: Dict[str, Any] = Field(..., description="Parking session KPIs")
    traffic: Dict[str, Any] = Field(..., description="Peak and least busy hour insights")
