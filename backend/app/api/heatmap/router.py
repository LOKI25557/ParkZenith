"""
FastAPI router definition for backend-side Heatmap proxy endpoints.
Parses query arguments, forwards requests to AI Service client, and handles error states.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Query, HTTPException, status

from backend.app.services.ai_service_client import ai_service_client
from backend.app.schemas.heatmap import (
    LiveHeatmapSchema,
    HistoricalHeatmapSchema,
    FacilityHeatmapSchema,
    ZoneAnalyticsSchema,
)

logger = logging.getLogger("backend.api.heatmap")

router = APIRouter(prefix="/heatmap", tags=["heatmap"])


def handle_client_response(res: dict):
    """
    Translates AI service response or throws appropriate FastAPI HTTP exceptions.
    """
    if not res.get("success", False):
        err = res.get("error", {})
        code = err.get("code")
        message = err.get("message", "AI Service encountered an error.")
        status_code = err.get("status_code", 500)

        if code in ("AI_SERVICE_UNAVAILABLE", "AI_SERVICE_TIMEOUT", "AI_SERVICE_DISABLED", "AI_SERVICE_INVALID_RESPONSE"):
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=message)
        elif code in ("MISSING_FACILITY", "EMPTY_DATASET"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        elif code in ("INVALID_DATE_RANGE", "INSUFFICIENT_DATA", "DUPLICATE_DATA"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
        else:
            raise HTTPException(status_code=status_code, detail=message)
    return res.get("data")


@router.get(
    "",
    response_model=LiveHeatmapSchema,
    status_code=status.HTTP_200_OK,
    summary="Get Heatmap Summary",
)
async def get_heatmap() -> LiveHeatmapSchema:
    """
    Forwards live heatmap request to AI service.
    """
    logger.info("Backend requesting overall heatmap.")
    res = await ai_service_client.get_heatmap()
    data = handle_client_response(res)
    return LiveHeatmapSchema(**data)


@router.get(
    "/live",
    response_model=LiveHeatmapSchema,
    status_code=status.HTTP_200_OK,
    summary="Get Live Heatmap",
)
async def get_heatmap_live() -> LiveHeatmapSchema:
    """
    Forwards live heatmap details request.
    """
    logger.info("Backend requesting live heatmap details.")
    res = await ai_service_client.get_heatmap_live()
    data = handle_client_response(res)
    return LiveHeatmapSchema(**data)


@router.get(
    "/history",
    response_model=HistoricalHeatmapSchema,
    status_code=status.HTTP_200_OK,
    summary="Get Historical Heatmap Trend",
)
async def get_heatmap_history(
    start_date: Optional[str] = Query(None, description="Start date of the range (UTC ISO format)"),
    end_date: Optional[str] = Query(None, description="End date of the range (UTC ISO format)"),
    interval: str = Query("hourly", description="Aggregation interval: hourly, daily, weekly, monthly"),
    facility_id: Optional[str] = Query(None, description="Facility ID filter"),
) -> HistoricalHeatmapSchema:
    """
    Forwards historical resampled heatmap request.
    """
    logger.info("Backend requesting historical heatmap. interval=%s", interval)
    res = await ai_service_client.get_heatmap_history(
        start_date=start_date,
        end_date=end_date,
        interval=interval,
        facility_id=facility_id,
    )
    data = handle_client_response(res)
    return HistoricalHeatmapSchema(**data)


@router.get(
    "/zones",
    response_model=ZoneAnalyticsSchema,
    status_code=status.HTTP_200_OK,
    summary="Get Zone Density Analytics",
)
async def get_heatmap_zones(
    facility_id: Optional[str] = Query(None, description="Filter by facility ID"),
    start_date: Optional[str] = Query(None, description="Start date of range (UTC)"),
    end_date: Optional[str] = Query(None, description="End date of range (UTC)"),
) -> ZoneAnalyticsSchema:
    """
    Forwards zone analytics request.
    """
    logger.info("Backend requesting zone density analytics.")
    res = await ai_service_client.get_heatmap_zones(
        facility_id=facility_id,
        start_date=start_date,
        end_date=end_date,
    )
    data = handle_client_response(res)
    return ZoneAnalyticsSchema(**data)


@router.get(
    "/facility/{facility_id}",
    response_model=FacilityHeatmapSchema,
    status_code=status.HTTP_200_OK,
    summary="Get Facility Heatmap",
)
async def get_heatmap_facility(facility_id: str) -> FacilityHeatmapSchema:
    """
    Forwards facility-specific live heatmap metrics.
    """
    logger.info("Backend requesting facility heatmap for ID: %s", facility_id)
    res = await ai_service_client.get_heatmap_facility(facility_id)
    data = handle_client_response(res)
    return FacilityHeatmapSchema(**data)
