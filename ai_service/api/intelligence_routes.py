"""
FastAPI router definition for Unified AI Intelligence Orchestrator API.
"""

import logging
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ai_service.api.deps import get_db_session
from ai_service.schemas.intelligence import IntelligenceRequest, IntelligenceResponse
from ai_service.services.intelligence_service import IntelligenceService
from ai_service.core.exceptions import MissingFacilityError, DatabaseError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/intelligence", tags=["Unified AI Intelligence Engine"])


def get_intelligence_service() -> IntelligenceService:
    """
    Dependency injection provider for IntelligenceService.
    """
    return IntelligenceService()


@router.post(
    "/decision",
    response_model=IntelligenceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Unified Parking Decision",
    description="Processes occupancy forecast, ETA, availability probability, and queue congestion to output a unified choice recommendation.",
)
async def get_unified_decision(
    req: IntelligenceRequest,
    db: AsyncSession = Depends(get_db_session),
    service: IntelligenceService = Depends(get_intelligence_service),
) -> IntelligenceResponse:
    """
    Accepts facility details and client coordinates, then runs the central intelligence orchestrator.
    """
    logger.info("Unified decision request received for facility ID: %s", req.facility_id)
    try:
        res = await service.get_decision(
            db=db,
            facility_id=req.facility_id,
            eta_minutes=req.eta_minutes,
            latitude=req.latitude,
            longitude=req.longitude,
            destination_latitude=req.destination_latitude,
            destination_longitude=req.destination_longitude,
        )
        return IntelligenceResponse(**res)
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
        logger.exception("Unified decision pipeline failed: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unified decision pipeline failed: {str(exc)}"
        ) from exc
