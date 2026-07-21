"""
ReservationHistory ORM Model.
"""

from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from ai_service.database.base import Base, current_utc_time


class ReservationHistory(Base):
    """
    Historical record of parking space reservations.
    """

    __tablename__ = "reservation_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reservation_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    facility_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    slot_id: Mapped[str] = mapped_column(String(64), nullable=False)
    reservation_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    reservation_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    reservation_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[float] = mapped_column(Float, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=current_utc_time, index=True
    )

    __table_args__ = (
        Index("idx_reservation_facility_start", "facility_id", "reservation_start"),
        Index("idx_reservation_status_facility", "reservation_status", "facility_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<ReservationHistory(id={self.id}, reservation_id='{self.reservation_id}', "
            f"facility_id='{self.facility_id}', status='{self.reservation_status}', "
            f"collected_at='{self.collected_at}')>"
        )
