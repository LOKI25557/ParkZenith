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



def get_backend_client() -> BackendAPIClient:
    """
    Dependency provider for BackendAPIClient instance.
    """
    return BackendAPIClient()


def get_collector_service(
    backend_client: BackendAPIClient = Depends(get_backend_client),
) -> CollectorService:
    """
    Dependency provider for CollectorService instance.
    """
    return CollectorService(backend_client=backend_client)


def get_exporter_service() -> ExporterService:
    """
    Dependency provider for ExporterService instance.
    """
    exporter = DatasetExporter()
    return ExporterService(exporter=exporter)

def get_analytics_service() -> AnalyticsService:
    """
    Dependency provider for AnalyticsService instance.
    """
    return AnalyticsService()


def get_preprocessing_service() -> PreprocessingService:
    """
    Dependency provider for PreprocessingService instance.
    """
    return PreprocessingService()


def get_forecasting_service() -> ForecastingService:
    """
    Dependency provider for ForecastingService instance.
    """
    return ForecastingService()


def get_availability_service() -> AvailabilityService:
    """
    Dependency provider for AvailabilityService instance.
    """
    return AvailabilityService()


def get_queue_service() -> QueueService:
    """
    Dependency provider for QueueService instance.
    """
    return QueueService()


def get_recommendation_service(
    forecasting_service: ForecastingService = Depends(get_forecasting_service),
    availability_service: AvailabilityService = Depends(get_availability_service),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    queue_service: QueueService = Depends(get_queue_service),
) -> RecommendationService:
    """
    Dependency provider for RecommendationService instance.
    """
    return RecommendationService(
        forecasting_service=forecasting_service,
        availability_service=availability_service,
        analytics_service=analytics_service,
        queue_service=queue_service,
    )


