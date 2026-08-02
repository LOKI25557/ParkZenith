"""
FastAPI router definition for Queue Prediction & Virtual Queue Operations.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ai_service.api.deps import get_db_session, get_queue_service
from ai_service.services.queue_service import QueueService
from ai_service.schemas.queue import (
    QueuePredictionResponse,
    QueueJoinRequest,
    QueueJoinResponse,
    QueueLeaveRequest,
    QueueLeaveResponse,
    QueuePositionResponse,
)

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
    res = await service.get_queue_prediction(db, facility_id, eta_minutes=0)
    return QueuePredictionResponse(**res)


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
    res = await service.get_queue_prediction(db, facility_id, eta_minutes=eta_minutes)
    return QueuePredictionResponse(**res)


# --- Real-Time Virtual Queue Endpoints ---

@router.post(
    "/{facility_id}/enqueue",
    response_model=QueueJoinResponse,
    status_code=status.HTTP_200_OK,
    summary="Join Virtual Queue",
    description="Enqueues a user in the facility virtual queue and returns the assigned position.",
)
async def enqueue_user(
    facility_id: str,
    req: QueueJoinRequest,
    db: AsyncSession = Depends(get_db_session),
    service: QueueService = Depends(get_queue_service),
) -> QueueJoinResponse:
    logger.info("Join queue request: facility=%s, user=%s", facility_id, req.user_id)
    pos = await service.enqueue_user(db, facility_id, req.user_id)
    return QueueJoinResponse(facility_id=facility_id, user_id=req.user_id, position=pos)


@router.post(
    "/{facility_id}/dequeue",
    response_model=QueueLeaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Pop or Dequeue from Virtual Queue",
    description="Removes the front driver (or a specific driver if user_id is provided) from the virtual queue.",
)
async def dequeue_user(
    facility_id: str,
    req: QueueLeaveRequest,
    db: AsyncSession = Depends(get_db_session),
    service: QueueService = Depends(get_queue_service),
) -> QueueLeaveResponse:
    logger.info("Dequeue request: facility=%s, user=%s", facility_id, req.user_id)
    popped_user = await service.dequeue_user(db, facility_id, req.user_id)
    success = popped_user is not None
    return QueueLeaveResponse(facility_id=facility_id, user_id=popped_user, success=success)


@router.post(
    "/{facility_id}/cancel",
    response_model=QueueLeaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel Queue Position",
    description="Removes a specific user from the virtual queue.",
)
async def cancel_user(
    facility_id: str,
    req: QueueJoinRequest,
    db: AsyncSession = Depends(get_db_session),
    service: QueueService = Depends(get_queue_service),
) -> QueueLeaveResponse:
    logger.info("Cancel queue spot request: facility=%s, user=%s", facility_id, req.user_id)
    cancelled = await service.cancel_user(db, facility_id, req.user_id)
    user_id = req.user_id if cancelled else None
    return QueueLeaveResponse(facility_id=facility_id, user_id=user_id, success=cancelled)


@router.get(
    "/{facility_id}/position",
    response_model=QueuePositionResponse,
    status_code=status.HTTP_200_OK,
    summary="Lookup Queue Position",
    description="Returns the current queue position of a user.",
)
async def get_user_position(
    facility_id: str,
    user_id: str = Query(..., min_length=1, description="Unique user ID to look up"),
    db: AsyncSession = Depends(get_db_session),
    service: QueueService = Depends(get_queue_service),
) -> QueuePositionResponse:
    logger.info("Queue position lookup: facility=%s, user=%s", facility_id, user_id)
    pos = await service.get_user_position(db, facility_id, user_id)
    return QueuePositionResponse(facility_id=facility_id, user_id=user_id, position=pos)
