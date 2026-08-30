from sqlalchemy import Column, Integer, ForeignKey, DateTime, Enum, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from .base import Base


class ReservationStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class Reservation(Base):
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    slot_id = Column(Integer, ForeignKey("parking_slots.id", ondelete="RESTRICT"), nullable=False, index=True)
    reservation_start = Column(DateTime(timezone=True), nullable=False, index=True)
    reservation_end = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(Enum(ReservationStatus), default=ReservationStatus.PENDING, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint('reservation_end > reservation_start', name='check_reservation_time'),
    )

    user = relationship("User", back_populates="reservations")
    slot = relationship("ParkingSlot", back_populates="reservations")
    session = relationship("ParkingSession", back_populates="reservation", uselist=False)
