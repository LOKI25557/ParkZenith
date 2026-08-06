"""
Pydantic schemas for backend Heatmap processing and API validation.
"""

from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class HeatmapPointSchema(BaseModel):
    latitude: float
    longitude: float
    intensity: float
    zone_id: Optional[str] = None
    facility_id: str


class ZoneDensitySchema(BaseModel):
    zone_id: str
    density_score: float
    occupancy_percentage: float
    occupied_slots: int
    total_slots: int
    intensity: float


class CongestionScoreSchema(BaseModel):
    congestion_index: float
    congestion_level: str
    capacity_utilization: float
    zone_utilization: float


class FacilityHeatmapSchema(BaseModel):
    facility_id: str
    facility_name: str
    latitude: float
    longitude: float
    overall_density: float
    overall_congestion_score: CongestionScoreSchema
    points: List[HeatmapPointSchema] = Field(default_factory=list)
    zones: List[ZoneDensitySchema] = Field(default_factory=list)


class LiveHeatmapSchema(BaseModel):
    timestamp: datetime
    facilities: List[FacilityHeatmapSchema]


class HistoricalHeatmapSchema(BaseModel):
    start_time: datetime
    end_time: datetime
    interval: str
    facilities: List[FacilityHeatmapSchema]


class PeakCongestionPeriodSchema(BaseModel):
    period: str
    density: float


class ZoneAnalyticsSchema(BaseModel):
    most_congested_zones: List[str] = Field(default_factory=list)
    least_occupied_zones: List[str] = Field(default_factory=list)
    average_density: float
    peak_congestion_periods: List[PeakCongestionPeriodSchema] = Field(default_factory=list)
    heatmap_summaries: Dict[str, str] = Field(default_factory=dict)
    zones: List[ZoneDensitySchema] = Field(default_factory=list)
