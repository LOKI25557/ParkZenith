"""
Pydantic schemas for backend-side prediction and recommendation validation.
"""

from typing import Optional, Dict
from pydantic import BaseModel, Field


class RecommendationRequestSchema(BaseModel):
    """
    Request validation schema for ranked parking recommendations on the backend.
    """
    latitude: float = Field(..., ge=-90.0, le=90.0, description="User's current latitude coordinates.")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="User's current longitude coordinates.")
    eta_minutes: int = Field(default=20, ge=0, description="Estimated arrival time in minutes.")
    destination_latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    destination_longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    max_distance_km: float = Field(default=5.0, gt=0.0)
    max_results: int = Field(default=5, gt=0)
    max_parking_fee: Optional[float] = Field(default=None, ge=0.0)
    parking_type: Optional[str] = Field(default=None)
    preferred_facility: Optional[str] = Field(default=None)
    accessibility_required: bool = Field(default=False)
    weights: Optional[Dict[str, float]] = Field(default=None)
