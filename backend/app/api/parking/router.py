from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.database.session import get_async_session
from backend.app.schemas.unified import UnifiedFacilityIntelligence, UnifiedRecommendationResponse
from backend.app.schemas.prediction import RecommendationRequestSchema
from backend.app.services.parking_intelligence_service import parking_intelligence_service

router = APIRouter(prefix="/parking", tags=["parking"])


@router.get("/ping")
async def ping_parking():
    return {"message": "parking placeholder"}


@router.get("/intelligence/{facility_id}", response_model=UnifiedFacilityIntelligence)
async def get_parking_intelligence(
    facility_id: int,
    eta_minutes: int = 20,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Unified endpoint that returns exact DB slot counts combined with AI predictive insights.
    """
    return await parking_intelligence_service.get_facility_intelligence(db, facility_id, eta_minutes)


@router.post("/recommend", response_model=UnifiedRecommendationResponse)
async def recommend_parking(
    req: RecommendationRequestSchema,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Unified endpoint that fetches AI recommendations and enriches them with real-time authoritative DB slot state.
    """
    return await parking_intelligence_service.get_enriched_recommendations(db, req)
