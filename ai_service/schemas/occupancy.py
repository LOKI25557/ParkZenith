"""
Pydantic schemas for OccupancyHistory data validation and serialization.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class OccupancyHistoryBase(BaseModel):
    """
    Base attributes for occupancy history record.
    """

    facility_id: str = Field(..., description="Unique identifier for parking facility", example="FAC-001")
    zone_id: Optional[str] = Field(default=None, description="Optional zone identifier within facility", example="ZONE-A")
    total_slots: int = Field(..., ge=0, description="Total parking capacity")
    occupied_slots: int = Field(..., ge=0, description="Number of currently occupied parking slots")
    available_slots: int = Field(..., ge=0, description="Number of currently available parking slots")
    occupancy_percentage: float = Field(..., ge=0.0, le=100.0, description="Percentage of occupied slots")


class OccupancyHistoryCreate(OccupancyHistoryBase):
    """
    Schema for creating a new occupancy history record.
    """

    collected_at: Optional[datetime] = Field(default=None, description="Collection timestamp")


class OccupancyHistoryResponse(OccupancyHistoryBase):
    """
    Response schema for returning an occupancy history record.
    """

    id: int
    collected_at: datetime

    model_config = ConfigDict(from_attributes=True)
