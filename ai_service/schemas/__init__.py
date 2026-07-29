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
from ai_service.schemas.analytics import (
    OverviewResponse,
    OccupancyAnalyticsResponse,
    UtilizationAnalyticsResponse,
    ReservationAnalyticsResponse,
    SessionAnalyticsResponse,
    PeakHoursResponse,
    TrendsResponse,
    ReportResponse,
)

from ai_service.schemas.preprocessing import (
    PipelineStatusResponse,
    PipelineRunResponse,
    FeaturesSummaryResponse,
    DatasetExportResponse,
    DatasetInfoResponse,
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
    "OverviewResponse",
    "OccupancyAnalyticsResponse",
    "UtilizationAnalyticsResponse",
    "ReservationAnalyticsResponse",
    "SessionAnalyticsResponse",
    "PeakHoursResponse",
    "TrendsResponse",
    "ReportResponse",
    "PipelineStatusResponse",
    "PipelineRunResponse",
    "FeaturesSummaryResponse",
    "DatasetExportResponse",
    "DatasetInfoResponse",
]

