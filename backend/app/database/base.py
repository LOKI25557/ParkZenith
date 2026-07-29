"""
Database Base Metadata module.
Imports all models to register their metadata with Base.
"""

from ..models.base import Base  # noqa
from ..models.user import User  # noqa
from ..models.parking import ParkingFacility, ParkingSlot  # noqa
from ..models.payment import Payment  # noqa
from ..models.reservation import Reservation  # noqa
from ..models.session import ParkingSession  # noqa
