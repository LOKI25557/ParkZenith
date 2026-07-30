"""
FastAPI router definition for Arrival Availability Prediction API.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ai_service.api.deps import get_db_session, get_availability_service
from ai_service.services.availability_service import AvailabilityService
from ai_service.schemas.availability import (
    AvailabilityRequest,
    AvailabilityResponse,
    AvailabilitySummary,
    AvailabilityStatus,
)
from ai_service.core.exceptions import MissingFacilityError, DatabaseError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/availability", tags=["Arrival Availability Prediction"])


@router.get(
    "/status",
    response_model=AvailabilityStatus,
    status_code=status.HTTP_200_OK,
    summary="Get Availability Service Status",
    description="Indicates whether the availability engine is ready and if forecasting models are loaded.",
)
async def get_availability_status(
    service: AvailabilityService = Depends(get_availability_service),
) -> AvailabilityStatus:
    """
    Returns service health and capability status.
    """
    logger.info("Availability status check requested.")
    res = await service.get_status()
    return AvailabilityStatus(**res)


@router.get(
    "/summary",
    response_model=AvailabilitySummary,
    status_code=status.HTTP_200_OK,
    summary="Get Summary Statistics",
    description="Returns summarized prediction statistics across all active facilities.",
)
async def get_availability_summary(
    eta_minutes: int = Query(20, ge=0, description="Estimated time of arrival in minutes"),
    db: AsyncSession = Depends(get_db_session),
    service: AvailabilityService = Depends(get_availability_service),
) -> AvailabilitySummary:
    """
    Returns summarized predictions for all tracked facilities.
    """
    logger.info("Availability summary requested for ETA: %d mins.", eta_minutes)
    res = await service.get_availability_summary(db, eta_minutes)
    return AvailabilitySummary(**res)


@router.get(
    "/{facility_id}",
    response_model=AvailabilityResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current Facility Availability",
    description="Returns availability prediction for a specific facility.",
)
async def get_facility_availability(
    facility_id: str,
    eta_minutes: int = Query(20, ge=0, description="Estimated time of arrival in minutes"),
    db: AsyncSession = Depends(get_db_session),
    service: AvailabilityService = Depends(get_availability_service),
) -> AvailabilityResponse:
    """
    Retrieves prediction for facility_id with query parameter eta_minutes.
    """
    logger.info("Availability check requested for facility: %s, ETA: %d mins", facility_id, eta_minutes)
    try:
        res = await service.predict_facility_availability(db, facility_id, eta_minutes)
        return AvailabilityResponse(**res)
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


@router.post(
    "/predict",
    response_model=AvailabilityResponse,
    status_code=status.HTTP_200_OK,
    summary="Predict Facility Availability at ETA",
    description="Predicts the availability probability and free slots for a specific facility at arrival.",
)
async def predict_availability(
    req: AvailabilityRequest,
    db: AsyncSession = Depends(get_db_session),
    service: AvailabilityService = Depends(get_availability_service),
) -> AvailabilityResponse:
    """
    Accepts request body and calculates parking space availability.
    """
    logger.info("Availability prediction requested: facility=%s, eta=%d", str(req.facility_id), req.eta_minutes)
    try:
        res = await service.predict_facility_availability(db, req.facility_id, req.eta_minutes)
        return AvailabilityResponse(**res)
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
