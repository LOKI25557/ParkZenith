"""
FastAPI router definition for Heatmap Intelligence Engine API.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ai_service.api.deps import get_db_session, get_heatmap_service
from ai_service.services.heatmap_service import HeatmapService
from ai_service.core.exceptions import MissingFacilityError, EmptyDatasetError, DatabaseError
from ai_service.schemas.heatmap import (
    LiveHeatmap,
    HistoricalHeatmap,
    FacilityHeatmap,
    ZoneAnalyticsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/heatmap", tags=["AI Heatmap Intelligence Engine"])


@router.get(
    "",
    response_model=LiveHeatmap,
    status_code=status.HTTP_200_OK,
    summary="Get Heatmap Summary",
    description="Calculates and returns real-time spatial parking density and congestion heatmap.",
)
async def get_heatmap(
    service: HeatmapService = Depends(get_heatmap_service),
    db: AsyncSession = Depends(get_db_session),
) -> LiveHeatmap:
    """
    General endpoint returning the current live heatmap.
    """
    logger.info("Live heatmap summary request received.")
    try:
        return await service.get_live_heatmap(db)
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exc.message
        ) from exc
    except Exception as exc:
        logger.exception("Failed to retrieve live heatmap: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve live heatmap: {str(exc)}"
        ) from exc


@router.get(
    "/live",
    response_model=LiveHeatmap,
    status_code=status.HTTP_200_OK,
    summary="Get Live Heatmap",
    description="Computes and retrieves current live heatmap data.",
)
async def get_heatmap_live(
    service: HeatmapService = Depends(get_heatmap_service),
    db: AsyncSession = Depends(get_db_session),
) -> LiveHeatmap:
    """
    Retrieves live heatmap details.
    """
    logger.info("Real-time live heatmap requested.")
    try:
        return await service.get_live_heatmap(db)
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exc.message
        ) from exc
    except Exception as exc:
        logger.exception("Failed to retrieve live heatmap: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve live heatmap: {str(exc)}"
        ) from exc


@router.get(
    "/history",
    response_model=HistoricalHeatmap,
    status_code=status.HTTP_200_OK,
    summary="Get Historical Heatmap Trend",
    description="Generates aggregated historical heatmap trend data grouped by interval.",
)
async def get_heatmap_history(
    start_date: Optional[datetime] = Query(None, description="Start date of the observation range (UTC). Defaults to 30 days ago."),
    end_date: Optional[datetime] = Query(None, description="End date of the range (UTC). Defaults to current time."),
    interval: str = Query("hourly", description="Resampling interval: hourly, daily, weekly, monthly."),
    facility_id: Optional[str] = Query(None, description="Optional facility ID filter."),
    service: HeatmapService = Depends(get_heatmap_service),
    db: AsyncSession = Depends(get_db_session),
) -> HistoricalHeatmap:
    """
    Fetches resampled historical heatmaps.
    """
    logger.info(
        "Historical heatmap requested. start_date=%s, end_date=%s, interval=%s, facility_id=%s",
        start_date, end_date, interval, facility_id
    )
    
    # Resolve default time range
    if not end_date:
        end_date = datetime.now(timezone.utc)
    if not start_date:
        start_date = end_date - timedelta(days=30)
        
    try:
        return await service.get_historical_heatmap(
            db=db,
            start_time=start_date,
            end_time=end_date,
            interval=interval,
            facility_id=facility_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        ) from exc
    except EmptyDatasetError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message
        ) from exc
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exc.message
        ) from exc
    except Exception as exc:
        logger.exception("Failed to retrieve historical heatmap: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve historical heatmap: {str(exc)}"
        ) from exc


@router.get(
    "/zones",
    response_model=ZoneAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Zone Density Analytics",
    description="Provides AI analytics summarizing zone utilization, congestion, and peak traffic periods.",
)
async def get_heatmap_zones(
    facility_id: Optional[str] = Query(None, description="Filter by facility ID"),
    start_date: Optional[datetime] = Query(None, description="Start date of range (UTC)"),
    end_date: Optional[datetime] = Query(None, description="End date of range (UTC)"),
    service: HeatmapService = Depends(get_heatmap_service),
    db: AsyncSession = Depends(get_db_session),
) -> ZoneAnalyticsResponse:
    """
    Compiles spatial density rankings and congestion periods.
    """
    logger.info("Zone density and traffic analytics requested.")
    try:
        return await service.get_zone_analytics(
            db=db,
            facility_id=facility_id,
            start_date=start_date,
            end_date=end_date,
        )
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exc.message
        ) from exc
    except Exception as exc:
        logger.exception("Failed to compile zone analytics: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compile zone analytics: {str(exc)}"
        ) from exc


@router.get(
    "/facility/{facility_id}",
    response_model=FacilityHeatmap,
    status_code=status.HTTP_200_OK,
    summary="Get Facility Heatmap",
    description="Calculates density and zone intensity metrics for a specific facility.",
)
async def get_heatmap_facility(
    facility_id: str,
    service: HeatmapService = Depends(get_heatmap_service),
    db: AsyncSession = Depends(get_db_session),
) -> FacilityHeatmap:
    """
    Fetches real-time heatmap metrics for a single facility.
    """
    logger.info("Facility heatmap requested for ID: %s", facility_id)
    try:
        live_data = await service.get_live_heatmap(db)
        # Find facility
        for f in live_data.facilities:
            if f.facility_id == facility_id:
                return f
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Facility '{facility_id}' not found in active heatmap data."
        )
    except HTTPException:
        raise
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exc.message
        ) from exc
    except Exception as exc:
        logger.exception("Failed to retrieve facility heatmap for ID %s: %s", facility_id, str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve facility heatmap: {str(exc)}"
        ) from exc
