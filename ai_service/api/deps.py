"""
FastAPI dependency injection utilities.
"""

from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ai_service.database.session import get_db_session
from ai_service.utils.backend_client import BackendAPIClient
from ai_service.utils.dataset_exporter import DatasetExporter
from ai_service.services.collector_service import CollectorService
from ai_service.services.exporter_service import ExporterService
from ai_service.services.analytics_service import AnalyticsService
from ai_service.services.preprocessing_service import PreprocessingService
from ai_service.services.forecasting_service import ForecastingService
from ai_service.services.availability_service import AvailabilityService
from ai_service.services.recommendation_service import RecommendationService
from ai_service.services.queue_service import QueueService
from ai_service.services.heatmap_service import HeatmapService



# Shared Singletons
_backend_client = BackendAPIClient()
_collector_service = CollectorService(backend_client=_backend_client)
_exporter_service = ExporterService(exporter=DatasetExporter())
_analytics_service = AnalyticsService()
_preprocessing_service = PreprocessingService()
_forecasting_service = ForecastingService()
_availability_service = AvailabilityService(forecasting_service=_forecasting_service)
_queue_service = QueueService()
_heatmap_service = HeatmapService()
_recommendation_service = RecommendationService(
    forecasting_service=_forecasting_service,
    availability_service=_availability_service,
    analytics_service=_analytics_service,
    queue_service=_queue_service,
)


def get_backend_client() -> BackendAPIClient:
    """
    Dependency provider for BackendAPIClient instance.
    """
    return _backend_client


def get_collector_service(
    backend_client: BackendAPIClient = Depends(get_backend_client),
) -> CollectorService:
    """
    Dependency provider for CollectorService instance.
    """
    return _collector_service


def get_exporter_service() -> ExporterService:
    """
    Dependency provider for ExporterService instance.
    """
    return _exporter_service


def get_analytics_service() -> AnalyticsService:
    """
    Dependency provider for AnalyticsService instance.
    """
    return _analytics_service


def get_preprocessing_service() -> PreprocessingService:
    """
    Dependency provider for PreprocessingService instance.
    """
    return _preprocessing_service


def get_forecasting_service() -> ForecastingService:
    """
    Dependency provider for ForecastingService instance.
    """
    return _forecasting_service


def get_availability_service() -> AvailabilityService:
    """
    Dependency provider for AvailabilityService instance.
    """
    return _availability_service


def get_queue_service() -> QueueService:
    """
    Dependency provider for QueueService instance.
    """
    return _queue_service


def get_recommendation_service() -> RecommendationService:
    """
    Dependency provider for RecommendationService instance.
    """
    return _recommendation_service


def get_heatmap_service() -> HeatmapService:
    """
    Dependency provider for HeatmapService instance.
    """
    return _heatmap_service




