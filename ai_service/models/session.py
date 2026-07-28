"""
ParkingSessionHistory ORM Model.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Float, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from ai_service.database.base import Base, current_utc_time


class ParkingSessionHistory(Base):
    """
    Historical record of parking sessions (vehicle entry, exit, duration, and fee).
    """

    __tablename__ = "parking_session_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    facility_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    vehicle_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    check_in_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    check_out_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    parking_fee: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=current_utc_time, index=True
    )

    __table_args__ = (
        Index("idx_session_facility_checkin", "facility_id", "check_in_time"),
        Index("idx_session_vehicle_facility", "vehicle_type", "facility_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<ParkingSessionHistory(id={self.id}, session_id='{self.session_id}', "
            f"facility_id='{self.facility_id}', vehicle_type='{self.vehicle_type}', "
            f"check_in='{self.check_in_time}')>"
        )
