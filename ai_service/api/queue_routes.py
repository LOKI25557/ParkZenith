"""
FastAPI router definition for Queue Prediction & Congestion Intelligence API.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ai_service.api.deps import get_db_session, get_queue_service
from ai_service.services.queue_service import QueueService
from ai_service.schemas.queue import QueuePredictionResponse
from ai_service.core.exceptions import MissingFacilityError, DatabaseError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/queue", tags=["Queue Prediction & Congestion Intelligence"])


@router.get(
    "/{facility_id}",
    response_model=QueuePredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current Queue Estimation",
    description="Returns current queue length, wait times, trend, and congestion classification for a facility.",
)
async def get_current_queue(
    facility_id: str,
    db: AsyncSession = Depends(get_db_session),
    service: QueueService = Depends(get_queue_service),
) -> QueuePredictionResponse:
    """
    Retrieves current queue estimation (ETA = 0 minutes).
    """
    logger.info("Current queue estimation requested for facility: %s", facility_id)
    try:
        res = await service.get_queue_prediction(db, facility_id, eta_minutes=0)
        return QueuePredictionResponse(**res)
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


@router.get(
    "/{facility_id}/prediction",
    response_model=QueuePredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Future Queue Prediction",
    description="Returns future predicted queue length, wait times, trend, and congestion classification at ETA.",
)
async def get_predicted_queue(
    facility_id: str,
    eta_minutes: int = Query(20, ge=0, description="Estimated time of arrival / prediction horizon in minutes"),
    db: AsyncSession = Depends(get_db_session),
    service: QueueService = Depends(get_queue_service),
) -> QueuePredictionResponse:
    """
    Retrieves queue prediction for facility_id at a future ETA horizon.
    """
    logger.info("Queue prediction requested for facility: %s, ETA: %d mins", facility_id, eta_minutes)
    try:
        res = await service.get_queue_prediction(db, facility_id, eta_minutes=eta_minutes)
        return QueuePredictionResponse(**res)
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
