"""
Schemas package initialization.
"""

from ai_service.schemas.occupancy import (
    OccupancyHistoryCreate,
    OccupancyHistoryResponse,
)
from ai_service.schemas.reservation import (
    ReservationHistoryCreate,
    ReservationHistoryResponse,
)
from ai_service.schemas.session import (
    ParkingSessionHistoryCreate,
    ParkingSessionHistoryResponse,
)
from ai_service.schemas.collector import (
    CollectionSummary,
    CollectorStatusResponse,
    ExportSummaryResponse,
)

__all__ = [
    "OccupancyHistoryCreate",
    "OccupancyHistoryResponse",
    "ReservationHistoryCreate",
    "ReservationHistoryResponse",
    "ParkingSessionHistoryCreate",
    "ParkingSessionHistoryResponse",
    "CollectionSummary",
    "CollectorStatusResponse",
    "ExportSummaryResponse",
]
