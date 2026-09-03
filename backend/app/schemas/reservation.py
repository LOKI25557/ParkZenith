from pydantic import BaseModel, model_validator
from typing import Optional
from datetime import datetime
from ..models.reservation import ReservationStatus


class ReservationBase(BaseModel):
    user_id: int
    slot_id: int
    reservation_start: datetime
    reservation_end: datetime


class ReservationCreate(BaseModel):
    slot_id: int
    reservation_start: datetime
    reservation_end: datetime

    @model_validator(mode='after')
    def check_time_range(self):
        if self.reservation_start and self.reservation_end and self.reservation_end <= self.reservation_start:
            raise ValueError("reservation_end must be after reservation_start")
        return self


class ReservationUpdate(BaseModel):
    status: Optional[ReservationStatus] = None


class ReservationRead(ReservationBase):
    id: int
    status: ReservationStatus

    class Config:
        orm_mode = True

class ReservationListResponse(BaseModel):
    items: list[ReservationRead]
    total: int
