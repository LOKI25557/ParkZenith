from pydantic import BaseModel
from typing import List, Optional, Any, Dict

class SlotInfo(BaseModel):
    id: int
    slot_number: str
    zone_id: int
    status: str

class ParkingSnapshotData(BaseModel):
    total_slots: int
    available_slots: int
    occupied_slots: int
    reserved_slots: int
    occupancy_percentage: float
    slots: List[SlotInfo]

class ParkingSnapshotEvent(BaseModel):
    event: str = "parking_snapshot"
    facility_id: int
    timestamp: str
    data: ParkingSnapshotData

class SlotStatusChangedEvent(BaseModel):
    event: str = "slot_status_changed"
    facility_id: int
    zone_id: int
    slot_id: int
    slot_number: str
    old_status: str
    new_status: str
    timestamp: str

class OccupancyData(BaseModel):
    total_slots: int
    available_slots: int
    occupied_slots: int
    reserved_slots: int
    occupancy_percentage: float

class OccupancyUpdatedEvent(BaseModel):
    event: str = "occupancy_updated"
    facility_id: int
    timestamp: str
    data: OccupancyData
