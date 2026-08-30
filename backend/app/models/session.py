from sqlalchemy import Column, Integer, ForeignKey, DateTime, Enum, Numeric, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from .base import Base


class ParkingSessionStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ParkingSession(Base):
    __tablename__ = "parking_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    slot_id = Column(Integer, ForeignKey("parking_slots.id", ondelete="RESTRICT"), nullable=False, index=True)
    reservation_id = Column(Integer, ForeignKey("reservations.id", ondelete="SET NULL"), nullable=True, index=True)
    check_in_time = Column(DateTime(timezone=True), nullable=False, index=True)
    check_out_time = Column(DateTime(timezone=True), nullable=True, index=True)
    duration_minutes = Column(Integer, nullable=True)
    status = Column(Enum(ParkingSessionStatus), nullable=False, default=ParkingSessionStatus.ACTIVE, index=True)
    fee_amount = Column(Numeric(10, 2), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint('duration_minutes >= 0', name='check_duration_minutes'),
    )

    user = relationship("User", back_populates="sessions")
    slot = relationship("ParkingSlot", back_populates="sessions")
    reservation = relationship("Reservation", back_populates="session")
    payment = relationship("Payment", back_populates="session", uselist=False)
