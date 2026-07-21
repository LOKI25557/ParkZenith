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
