"""
Models package initialization.
Exposes all ORM models for database table registration.
"""

from ai_service.models.occupancy import OccupancyHistory
from ai_service.models.reservation import ReservationHistory
from ai_service.models.session import ParkingSessionHistory

__all__ = [
    "OccupancyHistory",
    "ReservationHistory",
    "ParkingSessionHistory",
]
