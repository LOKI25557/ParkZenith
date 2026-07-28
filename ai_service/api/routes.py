"""
FastAPI Router for Data Collector control, status monitoring, and dataset exports.
"""

from typing import Dict
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ai_service.api.deps import (
    get_db_session,
    get_collector_service,
    get_exporter_service,
)
from ai_service.services.collector_service import CollectorService
from ai_service.services.exporter_service import ExporterService
from ai_service.schemas.collector import (
    CollectorStatusResponse,
    CollectionSummary,
    ExportSummaryResponse,
)

router = APIRouter(prefix="/collector", tags=["Data Collection Pipeline"])


@router.get(
    "/status",
    response_model=CollectorStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Collector Status",
    description="Returns total records stored in database, last collection timestamp, and current scheduler status.",
)
async def get_collector_status(
    collector_service: CollectorService = Depends(get_collector_service),
    db: AsyncSession = Depends(get_db_session),
) -> CollectorStatusResponse:
    """
    Get current collection status.
    """
    return await collector_service.get_status(db)


@router.get(
    "/run",
    response_model=Dict[str, CollectionSummary],
    status_code=status.HTTP_200_OK,
    summary="Manually Trigger Collectors",
    description="Triggers all data collectors (occupancy, reservations, sessions) on demand.",
)
async def run_collectors_manually(
    collector_service: CollectorService = Depends(get_collector_service),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, CollectionSummary]:
    """
    Manually run all data collectors.
    """
    return await collector_service.run_all_collectors(db)


@router.get(
    "/export",
    response_model=ExportSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Export History Datasets to CSV",
    description="Exports historical occupancy, reservation, and session tables to CSV files in the datasets directory.",
)
async def export_datasets(
    exporter_service: ExporterService = Depends(get_exporter_service),
    db: AsyncSession = Depends(get_db_session),
) -> ExportSummaryResponse:
    """
    Export all history tables to CSV format.
    """
    return await exporter_service.export_datasets(db)
