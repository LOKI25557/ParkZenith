from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime
from ..models.session import ParkingSessionStatus

class SessionBase(BaseModel):
    user_id: int
    slot_id: int
    reservation_id: Optional[int] = None
    check_in_time: datetime
    check_out_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    fee_amount: Optional[float] = None

class SessionCreate(BaseModel):
    slot_id: int
    reservation_id: Optional[int] = None

class SessionUpdate(BaseModel):
    status: Optional[ParkingSessionStatus] = None
    check_out_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    fee_amount: Optional[float] = None

class SessionRead(SessionBase):
    id: int
    status: ParkingSessionStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class SessionListResponse(BaseModel):
    items: List[SessionRead]
    total: int
