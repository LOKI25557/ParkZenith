from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ParkingFacilityBase(BaseModel):
    name: str
    address: Optional[str] = None
    city: Optional[str] = None


class ParkingFacilityRead(ParkingFacilityBase):
    id: int

    class Config:
        orm_mode = True


class ParkingSlotBase(BaseModel):
    facility_id: int
    slot_number: str
    is_available: Optional[bool] = True


class ParkingSlotRead(ParkingSlotBase):
    id: int

    class Config:
        orm_mode = True
