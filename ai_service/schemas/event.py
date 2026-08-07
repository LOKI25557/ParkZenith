"""
Event Pydantic Schemas.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class EventLocation(BaseModel):
    """
    Schema for event location details.
    """
    name: str = Field(..., description="Location name or address.", json_schema_extra={"example": "Zenith Stadium"})
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude coordinate.", json_schema_extra={"example": 12.9716})
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude coordinate.", json_schema_extra={"example": 77.5946})
    radius_of_influence: float = Field(1.0, ge=0.0, description="Radius of influence in kilometers.", json_schema_extra={"example": 2.0})


class Event(BaseModel):
    """
    Schema for full event details response.
    """
    event_id: str = Field(..., description="Unique event identifier.")
    name: str = Field(..., description="Name of the event.")
    type: str = Field(..., description="Category of event (e.g. Concert, Sports Event).")
    location: EventLocation = Field(..., description="Event location details.")
    expected_attendance: int = Field(..., ge=0, description="Expected attendance.")
    start_time: datetime = Field(..., description="Event start time (ISO format).")
    end_time: datetime = Field(..., description="Event end time (ISO format).")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score.")
    predicted_extra_demand: float = Field(..., description="Estimated baseline extra occupancy percentage.")
    congestion_multiplier: float = Field(..., ge=1.0, description="Congestion multiplier.")
    created_at: datetime = Field(..., description="Creation timestamp.")

    class Config:
        from_attributes = True


class EventCreate(BaseModel):
    """
    Schema for creating an event.
    """
    name: str = Field(..., description="Name of the event.")
    type: str = Field(..., description="Category of event.")
    location: EventLocation = Field(..., description="Event location details.")
    expected_attendance: int = Field(..., ge=0, description="Expected attendance.")
    start_time: datetime = Field(..., description="Event start time.")
    end_time: datetime = Field(..., description="Event end time.")
    confidence_score: float = Field(1.0, ge=0.0, le=1.0, description="Confidence score.")
    predicted_extra_demand: Optional[float] = Field(None, description="Optional baseline demand increase percentage.")
    congestion_multiplier: Optional[float] = Field(None, ge=1.0, description="Optional congestion multiplier.")


class EventUpdate(BaseModel):
    """
    Schema for updating an event.
    """
    name: Optional[str] = Field(None, description="Name of the event.")
    type: Optional[str] = Field(None, description="Category of event.")
    location: Optional[EventLocation] = Field(None, description="Event location details.")
    expected_attendance: Optional[int] = Field(None, ge=0, description="Expected attendance.")
    start_time: Optional[datetime] = Field(None, description="Event start time.")
    end_time: Optional[datetime] = Field(None, description="Event end time.")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score.")
    predicted_extra_demand: Optional[float] = Field(None, description="Baseline demand increase percentage.")
    congestion_multiplier: Optional[float] = Field(None, ge=1.0, description="Congestion multiplier.")


class EventImpact(BaseModel):
    """
    Schema representing estimated impact of an event on a parking facility.
    """
    event_id: str = Field(..., description="Unique event identifier.")
    facility_id: str = Field(..., description="Unique facility identifier.")
    distance_km: float = Field(..., description="Distance between event and facility in km.")
    attendance_impact: float = Field(..., description="Weighted attendance impact.")
    extra_occupancy_percentage: float = Field(..., description="Estimated extra occupancy percentage.")
    expected_congestion_level: str = Field(..., description="Expected congestion category (LOW, MEDIUM, HIGH, SEVERE).")
    queue_wait_increase_minutes: float = Field(..., description="Estimated queue wait time increase in minutes.")
    facility_utilization_increase_percentage: float = Field(..., description="Estimated facility utilization increase percentage.")
    parking_demand_surge_multiplier: float = Field(..., description="Parking demand surge multiplier.")
    travel_delay_minutes: float = Field(..., description="Estimated traffic/travel delay in minutes.")


class EventForecast(BaseModel):
    """
    Schema representing event-adjusted forecasting prediction.
    """
    facility_id: str = Field(..., description="Unique facility identifier.")
    target_time: datetime = Field(..., description="Forecast target timestamp.")
    original_predicted_occupancy: float = Field(..., description="Pre-event occupancy prediction percentage.")
    adjusted_predicted_occupancy: float = Field(..., description="Event-adjusted occupancy prediction percentage.")
    event_id: Optional[str] = Field(None, description="Active event identifier if any.")
    event_name: Optional[str] = Field(None, description="Active event name if any.")


class EventRecommendation(BaseModel):
    """
    Schema representing event-adjusted recommendation detail.
    """
    facility_id: str = Field(..., description="Unique facility identifier.")
    original_recommendation_score: float = Field(..., description="Original recommendation score (0.0 to 100.0).")
    adjusted_recommendation_score: float = Field(..., description="Event-adjusted recommendation score.")
    recommendation_status: str = Field(..., description="Status (GOOD_CHOICE, HIGH_DEMAND, LIMITED, UNLIKELY).")
    reasoning: List[str] = Field(..., description="Event-aware reasoning details.")
    alternative_suggested: bool = Field(..., description="Flag indicating if user should seek alternatives.")


class EventAnalytics(BaseModel):
    """
    Schema for event intelligence analytics dashboard.
    """
    most_impactful_events: List[Dict[str, Any]] = Field(..., description="List of events sorted by demand impact.")
    demand_increase_percentage: float = Field(..., description="Average parking demand increase percentage across facilities.")
    facility_impact_ranking: List[Dict[str, Any]] = Field(..., description="Facilities ranked by event impact frequency.")
    congestion_timeline: List[Dict[str, Any]] = Field(..., description="Hourly timeline of expected congestion peaks.")
    predicted_overflow_facilities: List[Dict[str, Any]] = Field(..., description="Facilities with risk of overflow (>=95% occupancy).")
    recommendation_effectiveness: float = Field(..., description="Estimated recommendation redirection success rate.")
    forecast_accuracy_improvement: float = Field(..., description="Forecast accuracy variance when adjusting for events.")


class EventSimulation(BaseModel):
    """
    Schema for creating mock event simulations.
    """
    simulation_name: str = Field(..., description="Name of the simulation template (e.g. Football match, Concert).")
    events: List[Event] = Field(..., description="Generated events inside the simulation.")
