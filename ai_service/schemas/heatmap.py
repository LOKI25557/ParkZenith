"""
Pydantic schemas for Heatmap points, Zone densities, Congestion scores, and Live/Historical heatmap responses.
"""

from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class HeatmapPoint(BaseModel):
    """
    Represents a geographical point with intensity mapping.
    """
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude coordinates of the heatmap point.")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude coordinates of the heatmap point.")
    intensity: float = Field(..., ge=0.0, le=100.0, description="Color intensity score from 0.0 to 100.0.")
    zone_id: Optional[str] = Field(default=None, description="Optional parking zone identifier.")
    facility_id: str = Field(..., description="Unique facility identifier.")


class ZoneDensity(BaseModel):
    """
    Represents density metrics for a specific zone.
    """
    zone_id: str = Field(..., description="Unique zone identifier.")
    density_score: float = Field(..., ge=0.0, le=100.0, description="Density score from 0.0 to 100.0.")
    occupancy_percentage: float = Field(..., ge=0.0, le=100.0, description="Occupancy percentage.")
    occupied_slots: int = Field(..., ge=0, description="Number of currently occupied slots.")
    total_slots: int = Field(..., ge=0, description="Total capacity slots in this zone.")
    intensity: float = Field(..., ge=0.0, le=100.0, description="Color intensity score mapping.")


class CongestionScore(BaseModel):
    """
    Detailed indicators of congestion for a facility or zone.
    """
    congestion_index: float = Field(..., ge=0.0, le=100.0, description="Numerical congestion index (0.0 to 100.0).")
    congestion_level: str = Field(..., description="Categorized level (LOW, MODERATE, HIGH, SEVERE).")
    capacity_utilization: float = Field(..., ge=0.0, le=100.0, description="Overall capacity utilization percentage.")
    zone_utilization: float = Field(..., ge=0.0, le=100.0, description="Average utilization across active zones.")


class FacilityHeatmap(BaseModel):
    """
    Grouped heatmap data for a specific parking facility.
    """
    facility_id: str = Field(..., description="Unique facility identifier.")
    facility_name: str = Field(..., description="Name of the parking facility.")
    latitude: float = Field(..., description="Latitude coordinate of the facility center.")
    longitude: float = Field(..., description="Longitude coordinate of the facility center.")
    overall_density: float = Field(..., ge=0.0, le=100.0, description="Average density of the facility.")
    overall_congestion_score: CongestionScore = Field(..., description="Detailed congestion metrics.")
    points: List[HeatmapPoint] = Field(default_factory=list, description="List of spatial heatmap points inside the facility.")
    zones: List[ZoneDensity] = Field(default_factory=list, description="Zone-specific density breakdown.")


class LiveHeatmap(BaseModel):
    """
    Real-time heatmap data snapshot.
    """
    timestamp: datetime = Field(..., description="Timestamp of live calculations.")
    facilities: List[FacilityHeatmap] = Field(..., description="Heatmap data for active facilities.")


class HistoricalHeatmap(BaseModel):
    """
    Heatmap trend data over a specified historical range.
    """
    start_time: datetime = Field(..., description="Start of historical observation range.")
    end_time: datetime = Field(..., description="End of historical range.")
    interval: str = Field(..., description="Aggregation interval (hourly, daily, weekly, monthly).")
    facilities: List[FacilityHeatmap] = Field(..., description="Aggregated historical facility heatmap states.")


class PeakCongestionPeriod(BaseModel):
    """
    Represents a peak period of high congestion.
    """
    period: str = Field(..., description="Time period descriptor (e.g. Hour/Day name).")
    density: float = Field(..., description="Average density recorded during this period.")


class ZoneAnalyticsResponse(BaseModel):
    """
    AI Analytics response summarizing zone utilization and traffic congestion.
    """
    most_congested_zones: List[str] = Field(default_factory=list, description="Zones with highest congestion.")
    least_occupied_zones: List[str] = Field(default_factory=list, description="Zones with lowest occupancy.")
    average_density: float = Field(..., description="Average density score across all zones.")
    peak_congestion_periods: List[PeakCongestionPeriod] = Field(default_factory=list, description="Key high-congestion time slots.")
    heatmap_summaries: Dict[str, str] = Field(default_factory=dict, description="Auto-generated descriptive summaries of zones.")
    zones: List[ZoneDensity] = Field(default_factory=list, description="Breakdown of zone densities.")
