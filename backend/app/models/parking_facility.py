from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Numeric, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class ParkingFacility(Base):
    __tablename__ = "parking_facilities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    address = Column(Text, nullable=False)
    city = Column(String(128), index=True, nullable=True)
    state = Column(String(128), nullable=True)
    postal_code = Column(String(32), nullable=True)
    latitude = Column(Numeric(9, 6), index=True, nullable=True)
    longitude = Column(Numeric(9, 6), index=True, nullable=True)
    total_slots = Column(Integer, nullable=False, default=0)
    operating_start_time = Column(String(16), nullable=True)  # e.g., "08:00"
    operating_end_time = Column(String(16), nullable=True)    # e.g., "22:00"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint('latitude >= -90 AND latitude <= 90', name='check_latitude'),
        CheckConstraint('longitude >= -180 AND longitude <= 180', name='check_longitude'),
        CheckConstraint('total_slots >= 0', name='check_total_slots_facility'),
    )

    zones = relationship("ParkingZone", back_populates="facility")
