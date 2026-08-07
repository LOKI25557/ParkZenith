"""
Event database model.
"""

from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from ai_service.database.base import Base, current_utc_time


class Event(Base):
    """
    ORM Model for external events affecting parking facilities.
    """

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    location_name: Mapped[str] = mapped_column(String(255), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    radius_of_influence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    expected_attendance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    predicted_extra_demand: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    congestion_multiplier: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=current_utc_time
    )

    __table_args__ = (
        Index("idx_events_time_range", "start_time", "end_time"),
        Index("idx_events_type_time", "type", "start_time"),
    )

    def __repr__(self) -> str:
        return (
            f"<Event(id={self.id}, event_id='{self.event_id}', name='{self.name}', "
            f"type='{self.type}', attendance={self.expected_attendance})>"
        )
