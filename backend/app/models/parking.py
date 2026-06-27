from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .base import Base


class ParkingFacility(Base):
    __tablename__ = "parking_facilities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    address = Column(Text, nullable=True)
    city = Column(String(128), nullable=True)
    is_active = Column(Boolean, default=True)

    slots = relationship("ParkingSlot", back_populates="facility")


class ParkingSlot(Base):
    __tablename__ = "parking_slots"

    id = Column(Integer, primary_key=True, index=True)
    facility_id = Column(Integer, ForeignKey("parking_facilities.id"), nullable=False)
    slot_number = Column(String(50), nullable=False)
    is_available = Column(Boolean, default=True)

    facility = relationship("ParkingFacility", back_populates="slots")
