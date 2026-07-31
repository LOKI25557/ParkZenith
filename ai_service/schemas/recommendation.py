"""
Pydantic schemas for Smart Recommendation Engine requests and responses.
"""

from typing import List, Optional, Dict, Union
from pydantic import BaseModel, Field, model_validator
from ai_service.recommendation.weights import WeightConfiguration


class RecommendationRequest(BaseModel):
    """
    Validation schema for parking recommendation requests.
    """
    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Current user latitude coordinates.",
        json_schema_extra={"example": 12.9716}
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Current user longitude coordinates.",
        json_schema_extra={"example": 77.5946}
    )
    eta_minutes: int = Field(
        default=20,
        ge=0,
        description="Estimated time of arrival at the parking facility in minutes.",
        json_schema_extra={"example": 20}
    )
    destination_latitude: Optional[float] = Field(
        default=None,
        ge=-90.0,
        le=90.0,
        description="Optional destination latitude coordinates for walking distance.",
        json_schema_extra={"example": 12.9750}
    )
    destination_longitude: Optional[float] = Field(
        default=None,
        ge=-180.0,
        le=180.0,
        description="Optional destination longitude coordinates for walking distance.",
        json_schema_extra={"example": 77.6000}
    )
    max_distance_km: float = Field(
        default=5.0,
        gt=0.0,
        description="Maximum search radius in kilometers.",
        json_schema_extra={"example": 5.0}
    )
    max_results: int = Field(
        default=5,
        gt=0,
        description="Maximum number of recommendations to return.",
        json_schema_extra={"example": 5}
    )
    max_parking_fee: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Optional limit on hourly parking cost."
    )
    parking_type: Optional[str] = Field(
        default=None,
        description="Optional type of parking space (e.g. Standard, EV, Covered)."
    )
    preferred_facility: Optional[str] = Field(
        default=None,
        description="Optional ID of preferred parking facility."
    )
    accessibility_required: bool = Field(
        default=False,
        description="Flag indicating if accessibility features are required."
    )
    weights: Optional[WeightConfiguration] = Field(
        default=None,
        description="Optional custom weights for scoring. Must sum to 1.0."
    )


class RecommendationItem(BaseModel):
    """
    Represents a single ranked facility recommendation.
    """
    rank: int = Field(..., description="Deterministically assigned rank index (1-based).")
    facility_id: Union[int, str] = Field(..., description="Unique identifier of the parking facility.")
    facility_name: str = Field(..., description="Display name of the facility.")
    recommendation_score: float = Field(..., description="Overall computed score (0-100). Higher is better.")
    availability_probability: float = Field(..., description="Probability (0-100%) that space will be available at ETA.")
    current_occupancy: float = Field(..., description="Current occupancy percentage.")
    forecast_occupancy: float = Field(..., description="Forecasted occupancy percentage at ETA.")
    distance_km: float = Field(..., description="Driving distance in kilometers from user location.")
    walking_distance_m: int = Field(..., description="Walking distance in meters from facility to destination.")
    estimated_cost: float = Field(..., description="Hourly parking rate or estimated fee.")
    queue_wait_minutes: float = Field(..., description="Estimated wait time in minutes at facility queue.")
    occupancy_risk: str = Field(..., description="Risk assessment (LOW, MEDIUM, HIGH).")
    confidence: float = Field(..., description="Prediction confidence percentage.")
    reason: str = Field(..., description="Human-readable explanation of the recommendation.")


class RecommendationResponse(BaseModel):
    """
    Response model for ranked parking recommendations.
    """
    recommendations: List[RecommendationItem] = Field(..., description="List of ranked facilities.")
    total_candidates: int = Field(..., description="Total facilities matching the search filter criteria.")
    returned_results: int = Field(..., description="Number of results returned.")


class RecommendationSummary(BaseModel):
    """
    Summarized recommendation view.
    """
    returned_results: int = Field(..., description="Number of top results.")
    top_recommendations: List[RecommendationItem] = Field(..., description="Top recommended facilities.")


class RecommendationStatus(BaseModel):
    """
    Service health and state schema.
    """
    status: str = Field(..., description="Current service state (e.g. READY, DEGRADED, INITIALIZING).")
    forecasting_service_ready: bool = Field(..., description="Indicates if occupancy forecasting models are loaded.")
    availability_service_ready: bool = Field(..., description="Indicates if availability predictor is active.")
    message: str = Field(..., description="Descriptive status details.")


class RecommendationScoreRequest(BaseModel):
    """
    Input schema for ad-hoc scoring endpoint.
    """
    availability_probability: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    current_occupancy: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    forecast_occupancy: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    distance_km: Optional[float] = Field(default=None, ge=0.0)
    walking_distance_m: Optional[float] = Field(default=None, ge=0.0)
    hourly_rate: Optional[float] = Field(default=None, ge=0.0)
    historical_utilization: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    queue_wait_minutes: Optional[float] = Field(default=None, ge=0.0)
    max_distance_km: float = Field(default=5.0, gt=0.0)
    weights: Optional[WeightConfiguration] = Field(default=None)


class RecommendationScoreResponse(BaseModel):
    """
    Response schema for ad-hoc scoring endpoint.
    """
    recommendation_score: float = Field(..., description="Computed overall score.")
    scores: Dict[str, float] = Field(..., description="Individual normalized factor scores.")
    reason: str = Field(..., description="Generated human explanation.")
