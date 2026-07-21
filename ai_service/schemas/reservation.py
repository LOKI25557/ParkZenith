"""
Pydantic schemas for ReservationHistory data validation and serialization.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ReservationHistoryBase(BaseModel):
    """
    Base attributes for reservation history record.
    """

    reservation_id: str = Field(..., description="Unique reservation ID from backend", example="RES-10023")
    facility_id: str = Field(..., description="Facility ID where reservation was made", example="FAC-001")
    slot_id: str = Field(..., description="Designated parking slot ID", example="SLOT-A12")
    reservation_status: str = Field(..., description="Reservation status (e.g. COMPLETED, CANCELLED, NO_SHOW)", example="COMPLETED")
    reservation_start: datetime = Field(..., description="Scheduled start datetime")
    reservation_end: datetime = Field(..., description="Scheduled end datetime")
    duration_minutes: float = Field(..., ge=0.0, description="Duration in minutes")


class ReservationHistoryCreate(ReservationHistoryBase):
    """
    Schema for creating a new reservation history record.
    """

    collected_at: Optional[datetime] = Field(default=None, description="Collection timestamp")


class ReservationHistoryResponse(ReservationHistoryBase):
    """
    Response schema for returning a reservation history record.
    """

    id: int
    collected_at: datetime

    model_config = ConfigDict(from_attributes=True)
