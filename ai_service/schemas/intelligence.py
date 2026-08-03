"""
Pydantic schemas for AI Intelligence Orchestration requests and responses.
"""

from typing import List, Optional, Union
from pydantic import BaseModel, Field


class AlternativeFacilityItem(BaseModel):
    """
    Represents a ranked alternative facility.
    """
    facility_id: str = Field(..., description="Unique identifier of the alternative facility.")
    score: float = Field(..., description="Calculated recommendation score (0.0 to 1.0).")


class IntelligenceRequest(BaseModel):
    """
    Request model for unified AI intelligence decisions.
    """
    facility_id: str = Field(..., description="Unique identifier of the parking facility.")
    eta_minutes: int = Field(default=20, ge=0, description="Estimated arrival time in minutes.")
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0, description="Optional user current latitude.")
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0, description="Optional user current longitude.")
    destination_latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0, description="Optional destination latitude.")
    destination_longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0, description="Optional destination longitude.")


class IntelligenceResponse(BaseModel):
    """
    Unified intelligence pipeline decision output.
    """
    facility_id: str = Field(..., description="Unique identifier of the parking facility.")
    eta_minutes: int = Field(..., description="Estimated arrival time in minutes.")
    predicted_occupancy: float = Field(..., description="Forecasted occupancy percentage at ETA.")
    predicted_available_slots: int = Field(..., description="Expected vacant slots count at ETA.")
    availability_probability: float = Field(..., description="Probability of space availability at ETA (0.0 to 1.0).")
    queue_wait_minutes: float = Field(..., description="Estimated virtual queue wait time in minutes at ETA.")
    confidence: float = Field(..., description="Unified confidence score for the prediction (0.0 to 1.0).")
    recommendation: str = Field(..., description="Decision recommendation category (e.g. GOOD_CHOICE, LIMITED, HIGH_DEMAND, UNLIKELY, UNKNOWN)")
    alternative_facilities: List[AlternativeFacilityItem] = Field(default_factory=list, description="Ranked alternative facilities if requested facility is risky.")
    reasoning: List[str] = Field(default_factory=list, description="Detailed explanatory bullet points.")
    prediction_status: str = Field(default="SUCCESS", description="Pipeline prediction execution status (SUCCESS or UNAVAILABLE).")
