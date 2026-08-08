"""
FastAPI router definition for the Aggregated AI Dashboard API.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, status, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ai_service.api.deps import get_db_session
from ai_service.schemas.dashboard import AIOverview
from ai_service.services.dashboard_service import DashboardService
from ai_service.core.exceptions import MissingFacilityError, DatabaseError

logger = logging.getLogger(__name__)

# Use prefix="/ai" to match the requested GET /ai/dashboard endpoint.
router = APIRouter(prefix="/ai", tags=["AI Dashboard Analytics & Intelligence Overview"])


def get_dashboard_service() -> DashboardService:
    """
    Dependency injection provider for DashboardService.
    """
    return DashboardService()


@router.get(
    "/dashboard",
    response_model=AIOverview,
    status_code=status.HTTP_200_OK,
    summary="Get Consolidated AI Analytics Dashboard",
    description="Aggregates and compiles all predictive and historical analytics into a single dashboard payload.",
)
async def get_ai_dashboard(
    facility_id: Optional[str] = Query(None, description="Filter by facility ID"),
    zone_id: Optional[str] = Query(None, description="Filter by zone ID"),
    start_date: Optional[datetime] = Query(None, description="Optional start date filter"),
    end_date: Optional[datetime] = Query(None, description="Optional end date filter"),
    event_id: Optional[str] = Query(None, description="Optional event ID filter"),
    eta_minutes: int = Query(20, ge=0, description="Estimated arrival offset in minutes"),
    latitude: Optional[float] = Query(None, ge=-90.0, le=90.0, description="Optional user latitude coordinates"),
    longitude: Optional[float] = Query(None, ge=-180.0, le=180.0, description="Optional user longitude coordinates"),
    db: AsyncSession = Depends(get_db_session),
    service: DashboardService = Depends(get_dashboard_service),
) -> AIOverview:
    """
    Consolidates occupancy, forecasts, arrival availability, virtual queues, heatmap zones,
    event-awareness, and performance metrics into a single response.
    """
    logger.info("AI Dashboard request received. facility_id: %s, eta: %d mins", facility_id, eta_minutes)
    try:
        res = await service.get_dashboard(
            db=db,
            facility_id=facility_id,
            zone_id=zone_id,
            start_date=start_date,
            end_date=end_date,
            event_id=event_id,
            eta_minutes=eta_minutes,
            latitude=latitude,
            longitude=longitude,
        )
        return AIOverview(**res)
    except MissingFacilityError as exc:
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
        logger.exception("AI Dashboard aggregation failed: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI Dashboard aggregation failed: {str(exc)}"
        ) from exc
