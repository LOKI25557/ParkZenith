from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from ..models.reservation import ReservationStatus


class ReservationBase(BaseModel):
    user_id: int
    slot_id: int
    start_time: datetime
    end_time: datetime


class ReservationRead(ReservationBase):
    id: int
    status: ReservationStatus

    class Config:
        orm_mode = True
