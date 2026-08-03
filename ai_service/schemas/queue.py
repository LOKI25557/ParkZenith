"""
Pydantic schemas for Queue Prediction & Congestion Intelligence.
"""

from datetime import datetime
from typing import Union, Literal, Optional
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
    estimated_wait_minutes: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Estimated waiting time in minutes."
    )
    queue_trend: Literal["DECREASING", "STABLE", "INCREASING", "RAPIDLY_INCREASING"] = Field(
        ...,
        description="Current queue trend classification."
    )
    congestion_level: Literal["LOW", "MODERATE", "HIGH", "SEVERE"] = Field(
        ...,
        description="Current congestion level classification."
    )
    congestion_status: Optional[str] = Field(
        default=None,
        description="Detailed congestion status (e.g. LOW, MODERATE, HIGH, CRITICAL)"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Prediction confidence score (0-100%)."
    )

    @field_validator("current_queue_length", "predicted_queue_length", "expected_arrivals", "expected_departures", "expected_wait_minutes", "estimated_wait_minutes")
    @classmethod
    def validate_non_negative(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0.0:
            raise ValueError("Value must be non-negative")
        return v

    @field_validator("confidence")
    @classmethod
    def validate_confidence_range(cls, v: float) -> float:
        if not (0.0 <= v <= 100.0):
            raise ValueError("Confidence must be between 0 and 100")
        return v


class QueueJoinRequest(BaseModel):
    """
    Schema for joining a virtual queue.
    """
    user_id: str = Field(..., min_length=1, description="Unique identifier for the user / driver.")


class QueueJoinResponse(BaseModel):
    """
    Response schema after joining a virtual queue.
    """
    facility_id: str = Field(..., description="Unique identifier of the parking facility.")
    user_id: str = Field(..., description="Unique identifier for the user.")
    position: int = Field(..., ge=1, description="Assigned queue position (1-based).")


class QueueLeaveRequest(BaseModel):
    """
    Schema for leaving or dequeuing from a virtual queue.
    """
    user_id: Optional[str] = Field(default=None, description="Optional user ID to dequeue. If omitted, the front of the queue is popped.")


class QueueLeaveResponse(BaseModel):
    """
    Response schema after leaving or dequeuing from a virtual queue.
    """
    facility_id: str = Field(..., description="Unique identifier of the parking facility.")
    user_id: Optional[str] = Field(default=None, description="The user ID that was dequeued (None if queue was empty).")
    success: bool = Field(..., description="True if a user was successfully dequeued.")


class QueuePositionResponse(BaseModel):
    """
    Response schema for checking current queue position.
    """
    facility_id: str = Field(..., description="Unique identifier of the parking facility.")
    user_id: str = Field(..., description="Unique identifier for the user.")
    position: Optional[int] = Field(default=None, description="Current queue position (1-based), or None if not enqueued.")

