from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from .base import Base


class ParkingSlotStatus(str, enum.Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    RESERVED = "reserved"


class VehicleType(str, enum.Enum):
    CAR = "car"
    BIKE = "bike"
    EV = "ev"
    OTHER = "other"


class ParkingSlot(Base):
    __tablename__ = "parking_slots"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("parking_zones.id", ondelete="CASCADE"), nullable=False, index=True)
    slot_number = Column(String(50), nullable=False)
    status = Column(Enum(ParkingSlotStatus), nullable=False, default=ParkingSlotStatus.AVAILABLE, index=True)
    vehicle_type = Column(Enum(VehicleType), nullable=False, default=VehicleType.CAR)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('zone_id', 'slot_number', name='uq_zone_slot_number'),
    )

    zone = relationship("ParkingZone", back_populates="slots")
    reservations = relationship("Reservation", back_populates="slot")
    sessions = relationship("ParkingSession", back_populates="slot")
