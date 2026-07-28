"""
Pydantic schemas for ParkingSessionHistory data validation and serialization.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ParkingSessionHistoryBase(BaseModel):
    """
    Base attributes for parking session history record.
    """

    session_id: str = Field(..., description="Unique parking session ID from backend", example="SESS-90041")
    facility_id: str = Field(..., description="Facility ID where parking occurred", example="FAC-001")
    vehicle_type: str = Field(..., description="Vehicle category (e.g., CAR, EV, SUV, BIKE)", example="CAR")
    check_in_time: datetime = Field(..., description="Vehicle entry timestamp")
    check_out_time: Optional[datetime] = Field(default=None, description="Vehicle exit timestamp")
    duration_minutes: Optional[float] = Field(default=None, ge=0.0, description="Session duration in minutes")
    parking_fee: Optional[float] = Field(default=None, ge=0.0, description="Total fee charged")


class ParkingSessionHistoryCreate(ParkingSessionHistoryBase):
    """
    Schema for creating a new parking session history record.
    """

    collected_at: Optional[datetime] = Field(default=None, description="Collection timestamp")


class ParkingSessionHistoryResponse(ParkingSessionHistoryBase):
    """
    Response schema for returning a parking session history record.
    """

    id: int
    collected_at: datetime

    model_config = ConfigDict(from_attributes=True)
