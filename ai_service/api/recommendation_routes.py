"""
FastAPI router definition for Smart Recommendation Engine API.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ai_service.api.deps import (
    get_db_session,
    get_forecasting_service,
    get_availability_service,
    get_analytics_service,
)
from ai_service.services.recommendation_service import RecommendationService
from ai_service.schemas.recommendation import (
    RecommendationRequest,
    RecommendationResponse,
    RecommendationItem,
    RecommendationStatus,
    RecommendationScoreRequest,
    RecommendationScoreResponse,
)
from ai_service.recommendation.scoring import RecommendationScorer
from ai_service.recommendation.explanation import generate_recommendation_reason

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recommendations", tags=["Smart Recommendation Engine"])


# Dependency injection provider for RecommendationService
def get_recommendation_service(
    db: AsyncSession = Depends(get_db_session),
) -> RecommendationService:
    """
    Instantiates RecommendationService with injected forecasting, availability, and analytics services.
    """
    from ai_service.api.deps import (
        get_forecasting_service,
        get_availability_service,
        get_analytics_service,
    )
    # Instantiate service dependencies
    forecasting = get_forecasting_service()
    availability = get_availability_service()
    analytics = get_analytics_service()
    return RecommendationService(
        forecasting_service=forecasting,
        availability_service=availability,
        analytics_service=analytics,
    )


@router.get(
    "/status",
    response_model=RecommendationStatus,
    status_code=status.HTTP_200_OK,
    summary="Get Recommendation Service Status",
    description="Indicates whether the recommendation engine and its predictive dependencies are ready.",
)
async def get_recommendation_status(
    service: RecommendationService = Depends(get_recommendation_service),
) -> RecommendationStatus:
    """
    Returns service health and status info.
    """
    logger.info("Recommendation service status check requested.")
    res = await service.get_status()
    return RecommendationStatus(**res)


@router.post(
    "",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Ranked Parking Recommendations",
    description="Analyzes multiple factors and returns a ranked list of recommended parking facilities.",
)
async def get_ranked_recommendations(
    req: RecommendationRequest,
    db: AsyncSession = Depends(get_db_session),
    service: RecommendationService = Depends(get_recommendation_service),
) -> RecommendationResponse:
    """
    Accepts coordinates and filters, then evaluates and ranks candidate facilities.
    """
    logger.info(
        "Ranked recommendations request received. User=(%f, %f)",
        req.latitude,
        req.longitude,
    )
    try:
        res = await service.get_recommendations(
            db=db,
            user_latitude=req.latitude,
            user_longitude=req.longitude,
            eta_minutes=req.eta_minutes,
            destination_latitude=req.destination_latitude,
            destination_longitude=req.destination_longitude,
            max_distance_km=req.max_distance_km,
            max_results=req.max_results,
            max_parking_fee=req.max_parking_fee,
            parking_type=req.parking_type,
            preferred_facility=req.preferred_facility,
            accessibility_required=req.accessibility_required,
            weights=req.weights,
        )
        return RecommendationResponse(**res)
    except Exception as exc:
        logger.exception("Failed to compute recommendations: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Recommendation evaluation failed: {str(exc)}",
        ) from exc


@router.get(
    "/top",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Top Recommendations",
    description="Shortcut endpoint to retrieve the single best recommended parking facility.",
)
async def get_top_recommendation(
    latitude: float = Query(..., ge=-90.0, le=90.0),
    longitude: float = Query(..., ge=-180.0, le=180.0),
    eta_minutes: int = Query(20, ge=0),
    destination_latitude: Optional[float] = Query(None, ge=-90.0, le=90.0),
    destination_longitude: Optional[float] = Query(None, ge=-180.0, le=180.0),
    max_distance_km: float = Query(5.0, gt=0.0),
    db: AsyncSession = Depends(get_db_session),
    service: RecommendationService = Depends(get_recommendation_service),
) -> RecommendationResponse:
    """
    Helper GET route returning the top available facility based on basic filters.
    """
    logger.info("Top recommendations shortcut requested.")
    try:
        res = await service.get_recommendations(
            db=db,
            user_latitude=latitude,
            user_longitude=longitude,
            eta_minutes=eta_minutes,
            destination_latitude=destination_latitude,
            destination_longitude=destination_longitude,
            max_distance_km=max_distance_km,
            max_results=3,  # Return top 3 for comparison
        )
        return RecommendationResponse(**res)
    except Exception as exc:
        logger.exception("Failed to query top recommendations: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Querying top recommendations failed: {str(exc)}",
        ) from exc


@router.get(
    "/{facility_id}",
    response_model=RecommendationItem,
    status_code=status.HTTP_200_OK,
    summary="Get Specific Facility Recommendation Details",
    description="Returns scoring breakdown and description rationale for a specific facility ID.",
)
async def get_facility_recommendation_details(
    facility_id: str,
    latitude: float = Query(..., ge=-90.0, le=90.0),
    longitude: float = Query(..., ge=-180.0, le=180.0),
    eta_minutes: int = Query(20, ge=0),
    destination_latitude: Optional[float] = Query(None, ge=-90.0, le=90.0),
    destination_longitude: Optional[float] = Query(None, ge=-180.0, le=180.0),
    db: AsyncSession = Depends(get_db_session),
    service: RecommendationService = Depends(get_recommendation_service),
) -> RecommendationItem:
    """
    Returns detailed scoring calculations for a specific facility.
    """
    logger.info("Details requested for facility_id: %s", facility_id)
    try:
        res = await service.get_facility_recommendation_detail(
            db=db,
            facility_id=facility_id,
            user_latitude=latitude,
            user_longitude=longitude,
            eta_minutes=eta_minutes,
            destination_latitude=destination_latitude,
            destination_longitude=destination_longitude,
        )
        return RecommendationItem(**res)
    except Exception as exc:
        logger.exception("Failed to retrieve details for facility %s: %s", facility_id, str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compile recommendation details for facility: {str(exc)}",
        ) from exc


@router.post(
    "/score",
    response_model=RecommendationScoreResponse,
    status_code=status.HTTP_200_OK,
    summary="Ad-hoc Score Calculator Utility",
    description="Calculates normalized scores and weights combination for direct facility inputs (used for testing/debugging).",
)
async def calculate_adhoc_score(
    req: RecommendationScoreRequest,
) -> RecommendationScoreResponse:
    """
    Utility endpoint that runs scoring algorithms directly on input values.
    """
    logger.info("Ad-hoc recommendation scoring calculation requested.")
    scorer = RecommendationScorer(weights=req.weights)

    data = {
        "availability_probability": req.availability_probability,
        "current_occupancy": req.current_occupancy,
        "forecast_occupancy": req.forecast_occupancy,
        "distance_km": req.distance_km,
        "walking_distance_m": req.walking_distance_m,
        "estimated_cost": req.hourly_rate,
        "historical_utilization": req.historical_utilization,
        "queue_wait_minutes": req.queue_wait_minutes,
    }

    scores = scorer.calculate_scores(data, req.max_distance_km)
    final_score = scorer.calculate_final_score(scores)
    reason = generate_recommendation_reason(scores)

    return RecommendationScoreResponse(
        recommendation_score=final_score,
        scores=scores,
        reason=reason,
    )
