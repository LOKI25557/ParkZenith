"""
Pydantic schemas for Arrival Availability Prediction requests, responses, and summaries.
"""

from typing import List, Union
from pydantic import BaseModel, Field


class AvailabilityRequest(BaseModel):
    """
    Request model for predicting parking slot availability at estimated arrival time.
    """
    facility_id: Union[int, str] = Field(
        ...,
        description="Unique identifier of the parking facility.",
        json_schema_extra={"example": 1}
    )
    eta_minutes: int = Field(
        ...,
        ge=0,
        description="Estimated time of arrival in minutes from now.",
        json_schema_extra={"example": 20}
    )


class AvailabilityResponse(BaseModel):
    """
    Response model for arrival availability prediction.
    """
    facility_id: Union[int, str] = Field(..., description="Unique identifier of the parking facility.")
    eta_minutes: int = Field(..., description="Estimated time of arrival in minutes from now.")
    current_occupancy: float = Field(..., description="Current occupancy percentage of the facility.")
    forecast_occupancy: float = Field(..., description="Forecasted occupancy percentage at the ETA.")
    expected_free_slots: int = Field(..., description="Expected number of vacant parking slots at the ETA.")
    availability_probability: float = Field(..., description="Probability (0-100%) that space will be available at ETA.")
    occupancy_risk: str = Field(..., description="Level of occupancy risk at ETA: LOW, MEDIUM, or HIGH.")
    confidence: float = Field(..., description="Prediction confidence score (0-100%).")


class AvailabilitySummary(BaseModel):
    """
    Response model for summarized availability prediction statistics across facilities.
    """
    total_facilities_predicted: int = Field(..., description="Total number of facilities processed.")
    average_probability: float = Field(..., description="Average availability probability across facilities.")
    average_confidence: float = Field(..., description="Average prediction confidence across facilities.")
    high_risk_count: int = Field(..., description="Number of facilities with HIGH occupancy risk.")
    medium_risk_count: int = Field(..., description="Number of facilities with MEDIUM occupancy risk.")
    low_risk_count: int = Field(..., description="Number of facilities with LOW occupancy risk.")
    predictions: List[AvailabilityResponse] = Field(..., description="Detail list of predictions.")


class AvailabilityStatus(BaseModel):
    """
    Response model representing availability service operational status.
    """
    status: str = Field(..., description="Service status, e.g., 'READY' or 'INITIALIZING'.")
    forecasting_service_ready: bool = Field(..., description="Indicates if the forecasting ML service is loaded.")
    message: str = Field(..., description="Status description message.")
