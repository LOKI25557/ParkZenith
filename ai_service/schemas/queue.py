"""
Pydantic schemas for Queue Prediction & Congestion Intelligence.
"""

from datetime import datetime
from typing import Union, Literal
from pydantic import BaseModel, Field, field_validator


class QueuePredictionRequest(BaseModel):
    """
    Request model for retrieving queue prediction.
    """
    facility_id: Union[int, str] = Field(
        ...,
        description="Unique identifier of the parking facility.",
        json_schema_extra={"example": "FAC-001"}
    )
    eta_minutes: int = Field(
        default=0,
        ge=0,
        description="Estimated time of arrival (or prediction horizon) in minutes.",
        json_schema_extra={"example": 20}
    )


class QueuePredictionResponse(BaseModel):
    """
    Response model for queue prediction and congestion metrics.
    """
    facility_id: Union[int, str] = Field(..., description="Unique identifier of the parking facility.")
    timestamp: datetime = Field(..., description="Timestamp of the queue prediction.")
    current_queue_length: float = Field(
        ...,
        ge=0.0,
        description="Estimated current queue length (number of vehicles)."
    )
    predicted_queue_length: float = Field(
        ...,
        ge=0.0,
        description="Predicted queue length at the target horizon (ETA)."
    )
    expected_arrivals: float = Field(
        ...,
        ge=0.0,
        description="Expected arrivals during the ETA horizon."
    )
    expected_departures: float = Field(
        ...,
        ge=0.0,
        description="Expected departures during the ETA horizon."
    )
    expected_wait_minutes: float = Field(
        ...,
        ge=0.0,
        description="Expected waiting time in minutes to enter the facility."
    )
    queue_trend: Literal["DECREASING", "STABLE", "INCREASING", "RAPIDLY_INCREASING"] = Field(
        ...,
        description="Current queue trend classification."
    )
    congestion_level: Literal["LOW", "MODERATE", "HIGH", "SEVERE"] = Field(
        ...,
        description="Current congestion level classification."
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Prediction confidence score (0-100%)."
    )

    @field_validator("current_queue_length", "predicted_queue_length", "expected_arrivals", "expected_departures", "expected_wait_minutes")
    @classmethod
    def validate_non_negative(cls, v: float) -> float:
        if v < 0.0:
            raise ValueError("Value must be non-negative")
        return v

    @field_validator("confidence")
    @classmethod
    def validate_confidence_range(cls, v: float) -> float:
        if not (0.0 <= v <= 100.0):
            raise ValueError("Confidence must be between 0 and 100")
        return v
