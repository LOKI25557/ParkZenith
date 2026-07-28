"""
OccupancyHistory ORM Model.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Float, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from ai_service.database.base import Base, current_utc_time


class OccupancyHistory(Base):
    """
    Historical record of facility and zone occupancy metrics.
    """

    __tablename__ = "occupancy_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    facility_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    zone_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    total_slots: Mapped[int] = mapped_column(Integer, nullable=False)
    occupied_slots: Mapped[int] = mapped_column(Integer, nullable=False)
    available_slots: Mapped[int] = mapped_column(Integer, nullable=False)
    occupancy_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=current_utc_time, index=True
    )

    __table_args__ = (
        Index("idx_occupancy_facility_collected", "facility_id", "collected_at"),
        Index("idx_occupancy_facility_zone", "facility_id", "zone_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<OccupancyHistory(id={self.id}, facility_id='{self.facility_id}', "
            f"zone_id='{self.zone_id}', percentage={self.occupancy_percentage}%, "
            f"collected_at='{self.collected_at}')>"
        )
