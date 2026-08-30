from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class ParkingZone(Base):
    __tablename__ = "parking_zones"

    id = Column(Integer, primary_key=True, index=True)
    facility_id = Column(Integer, ForeignKey("parking_facilities.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    floor_number = Column(Integer, nullable=True)
    total_slots = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('facility_id', 'name', name='uq_facility_zone_name'),
        CheckConstraint('total_slots >= 0', name='check_total_slots_zone'),
    )

    facility = relationship("ParkingFacility", back_populates="zones")
    slots = relationship("ParkingSlot", back_populates="zone")
