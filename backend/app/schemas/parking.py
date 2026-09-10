from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum
from backend.app.models.parking_slot import ParkingSlotStatus, VehicleType

# ----------------- #
# PARKING FACILITY  #
# ----------------- #

class FacilityBase(BaseModel):
    name: str
    description: Optional[str] = None
    address: str
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180)
    total_slots: Optional[int] = Field(0, ge=0)
    operating_start_time: Optional[str] = None
    operating_end_time: Optional[str] = None
    is_active: Optional[bool] = True

class FacilityCreate(FacilityBase):
    pass

class FacilityUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180)
    total_slots: Optional[int] = Field(None, ge=0)
    operating_start_time: Optional[str] = None
    operating_end_time: Optional[str] = None
    is_active: Optional[bool] = None

class FacilityResponse(FacilityBase):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ----------------- #
# PARKING ZONE      #
# ----------------- #

class ZoneBase(BaseModel):
    name: str
    description: Optional[str] = None
    floor_number: Optional[int] = None
    total_slots: Optional[int] = Field(0, ge=0)
    is_active: Optional[bool] = True

class ZoneCreate(ZoneBase):
    pass

class ZoneUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    floor_number: Optional[int] = None
    total_slots: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None

class ZoneResponse(ZoneBase):
    id: int
    facility_id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ----------------- #
# PARKING SLOT      #
# ----------------- #

class SlotBase(BaseModel):
    slot_number: str
    status: Optional[ParkingSlotStatus] = ParkingSlotStatus.AVAILABLE
    vehicle_type: Optional[VehicleType] = VehicleType.CAR
    is_active: Optional[bool] = True

class SlotCreate(SlotBase):
    pass

class SlotUpdate(BaseModel):
    slot_number: Optional[str] = None
    status: Optional[ParkingSlotStatus] = None
    vehicle_type: Optional[VehicleType] = None
    is_active: Optional[bool] = None

class SlotStatusUpdate(BaseModel):
    status: ParkingSlotStatus

class SlotResponse(SlotBase):
    id: int
    zone_id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ----------------- #
# AVAILABILITY      #
# ----------------- #

class AvailabilityResponse(BaseModel):
    entity_id: int  # Either facility_id or zone_id
    total_slots: int
    available: int
    occupied: int
    reserved: int
    occupancy_percentage: float
