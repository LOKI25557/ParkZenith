"""
FastAPI router definition for Event Intelligence API.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ai_service.api.deps import get_db_session, get_forecasting_service, get_recommendation_service
from ai_service.schemas.event import (
    Event,
    EventCreate,
    EventUpdate,
    EventImpact,
    EventForecast,
    EventRecommendation,
    EventAnalytics,
    EventSimulation,
)
from ai_service.services.event_service import EventIntelligenceService
from ai_service.services.event_impact_engine import EventImpactEngine
from sqlalchemy import select
from ai_service.models.occupancy import OccupancyHistory
from ai_service.recommendation.weights import get_facility_metadata

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["Event-Aware Intelligence"])


def get_event_service() -> EventIntelligenceService:
    """
    Dependency injection provider for EventIntelligenceService.
    """
    return EventIntelligenceService()


@router.post(
    "",
    response_model=Event,
    status_code=status.HTTP_201_CREATED,
    summary="Create Event",
    description="Registers a new external event affecting parking analytics.",
)
async def create_event(
    event_in: EventCreate,
    db: AsyncSession = Depends(get_db_session),
    service: EventIntelligenceService = Depends(get_event_service),
) -> Event:
    try:
        return await service.create_event(db, event_in)
    except Exception as exc:
        logger.exception("Failed to create event: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create event: {str(exc)}"
        )


@router.get(
    "",
    response_model=List[Event],
    summary="List Events",
    description="Lists registered events with optional type filtering.",
)
async def list_events(
    skip: int = 0,
    limit: int = 100,
    type_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
    service: EventIntelligenceService = Depends(get_event_service),
) -> List[Event]:
    return await service.get_events(db, skip=skip, limit=limit, type_filter=type_filter)


@router.get(
    "/upcoming",
    response_model=List[Event],
    summary="Get Upcoming Events",
    description="Lists events scheduled in the future.",
)
async def get_upcoming_events(
    db: AsyncSession = Depends(get_db_session),
    service: EventIntelligenceService = Depends(get_event_service),
) -> List[Event]:
    return await service.get_upcoming_events(db)


@router.get(
    "/active",
    response_model=List[Event],
    summary="Get Active Events",
    description="Lists events currently active or near start/end.",
)
async def get_active_events(
    db: AsyncSession = Depends(get_db_session),
    service: EventIntelligenceService = Depends(get_event_service),
) -> List[Event]:
    return await service.get_active_events(db)


@router.get(
    "/analytics",
    response_model=EventAnalytics,
    summary="Get Event Analytics Dashboard",
    description="Generates advanced analytics relating to event impact and parking overflow risks.",
)
async def get_event_analytics(
    db: AsyncSession = Depends(get_db_session),
    service: EventIntelligenceService = Depends(get_event_service),
) -> EventAnalytics:
    try:
        res = await service.get_analytics(db)
        return EventAnalytics(**res)
    except Exception as exc:
        logger.exception("Failed to get event analytics: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get event analytics: {str(exc)}"
        )


@router.post(
    "/simulations",
    response_model=List[Event],
    summary="Run Event Simulations",
    description="Generates realistic simulation event datasets in the database.",
)
async def run_simulations(
    simulation_name: str,
    db: AsyncSession = Depends(get_db_session),
    service: EventIntelligenceService = Depends(get_event_service),
) -> List[Event]:
    try:
        return await service.run_simulations(db, simulation_name)
    except Exception as exc:
        logger.exception("Simulation execution failed: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation execution failed: {str(exc)}"
        )


@router.get(
    "/forecast",
    response_model=EventForecast,
    summary="Get Event-Adjusted Forecast",
    description="Returns event-adjusted occupancy forecasting predictions.",
)
async def get_event_forecast(
    facility_id: str,
    horizon_minutes: int,
    db: AsyncSession = Depends(get_db_session),
    service: EventIntelligenceService = Depends(get_event_service),
    forecasting_service = Depends(get_forecasting_service),
) -> EventForecast:
    if horizon_minutes not in (15, 30, 60):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Horizon minutes must be 15, 30, or 60."
        )

    # 1. Fetch base forecast
    try:
        f_res = await forecasting_service.get_forecast_snapshot(
            db=db,
            facility_id=int(facility_id) if facility_id.isdigit() else facility_id,
            primary_horizon_minutes=horizon_minutes
        )
        base_occ = f_res.get(f"prediction_{horizon_minutes}", 50.0)
    except Exception as exc:
        logger.warning("Failed to get base occupancy forecast: %s", str(exc))
        base_occ = 50.0

    # 2. Query event adjustments
    target_time = datetime.now(timezone.utc) + timedelta(minutes=horizon_minutes)
    composite = await service.get_composite_impact(db, facility_id, target_time)
    extra_occ = composite.get("composite_extra_occupancy_percentage", 0.0)

    adjusted_occ = base_occ + extra_occ
    adjusted_occ = min(100.0, max(0.0, adjusted_occ))

    return EventForecast(
        facility_id=facility_id,
        target_time=target_time,
        original_predicted_occupancy=round(base_occ, 2),
        adjusted_predicted_occupancy=round(adjusted_occ, 2),
        event_id=composite.get("dominant_event_id"),
        event_name=composite.get("dominant_event_name"),
    )


@router.get(
    "/recommendations",
    response_model=List[EventRecommendation],
    summary="Get Event-Adjusted Recommendations",
    description="Returns event-adjusted recommendations for parking facilities.",
)
async def get_event_recommendations(
    user_latitude: float,
    user_longitude: float,
    eta_minutes: int = 20,
    destination_latitude: Optional[float] = None,
    destination_longitude: Optional[float] = None,
    db: AsyncSession = Depends(get_db_session),
    service: EventIntelligenceService = Depends(get_event_service),
    recommendation_service = Depends(get_recommendation_service),
) -> List[EventRecommendation]:
    # 1. Query standard recommendations
    try:
        rec_res = await recommendation_service.get_recommendations(
            db=db,
            user_latitude=user_latitude,
            user_longitude=user_longitude,
            eta_minutes=eta_minutes,
            destination_latitude=destination_latitude,
            destination_longitude=destination_longitude,
            max_results=5,
        )
        candidates = rec_res.get("recommendations", [])
    except Exception as exc:
        logger.exception("Failed to get recommendations: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recommendations: {str(exc)}"
        )

    # 2. Adjust for events
    adjusted = []
    target_time = datetime.now(timezone.utc) + timedelta(minutes=eta_minutes)

    for item in candidates:
        fid = str(item["facility_id"])
        base_score = float(item["recommendation_score"])
        base_status = item.get("occupancy_risk", "LOW")

        composite = await service.get_composite_impact(db, fid, target_time)
        cong_mult = composite.get("composite_congestion_multiplier", 1.0)
        extra_occ = composite.get("composite_extra_occupancy_percentage", 0.0)

        # Penalize score
        adjusted_score = base_score / cong_mult
        adjusted_score = max(0.0, min(100.0, adjusted_score))

        # Adjust status
        status_str = "GOOD_CHOICE"
        if adjusted_score < 40.0:
            status_str = "UNLIKELY"
        elif extra_occ >= 20.0 or cong_mult >= 1.5:
            status_str = "HIGH_DEMAND"
        elif adjusted_score < 70.0:
            status_str = "LIMITED"

        reasoning = []
        alt_suggested = False
        if composite["events_count"] > 0:
            ev_name = composite["dominant_event_name"]
            reasoning.append(f"Heavy congestion expected due to nearby event: {ev_name}")
            reasoning.append(f"Arrive at least 30 minutes early to secure parking.")
            alt_suggested = True
        else:
            reasoning.append("Normal parking conditions predicted.")

        adjusted.append(
            EventRecommendation(
                facility_id=fid,
                original_recommendation_score=round(base_score, 2),
                adjusted_recommendation_score=round(adjusted_score, 2),
                recommendation_status=status_str,
                reasoning=reasoning,
                alternative_suggested=alt_suggested,
            )
        )

    return adjusted


@router.get(
    "/{event_id}",
    response_model=Event,
    summary="Get Event Detail",
    description="Retrieves a single event details by its event_id.",
)
async def get_event_detail(
    event_id: str,
    db: AsyncSession = Depends(get_db_session),
    service: EventIntelligenceService = Depends(get_event_service),
) -> Event:
    ev = await service.get_event_by_id(db, event_id)
    if not ev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID '{event_id}' not found."
        )
    return ev


@router.put(
    "/{event_id}",
    response_model=Event,
    summary="Update Event",
    description="Updates attributes of an existing event.",
)
async def update_event(
    event_id: str,
    event_in: EventUpdate,
    db: AsyncSession = Depends(get_db_session),
    service: EventIntelligenceService = Depends(get_event_service),
) -> Event:
    ev = await service.update_event(db, event_id, event_in)
    if not ev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID '{event_id}' not found."
        )
    return ev


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Event",
    description="Deletes an event from registered database list.",
)
async def delete_event(
    event_id: str,
    db: AsyncSession = Depends(get_db_session),
    service: EventIntelligenceService = Depends(get_event_service),
):
    success = await service.delete_event(db, event_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID '{event_id}' not found."
        )


@router.get(
    "/{event_id}/impact",
    response_model=List[EventImpact],
    summary="Get Event Impacts on Facilities",
    description="Calculates demand and congestion impacts of a single event on all active facilities.",
)
async def get_event_impact(
    event_id: str,
    db: AsyncSession = Depends(get_db_session),
    service: EventIntelligenceService = Depends(get_event_service),
) -> List[EventImpact]:
    # 1. Fetch event
    ev = await service.get_event_by_id(db, event_id)
    if not ev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID '{event_id}' not found."
        )

    # 2. Iterate active facilities and compute impact
    facilities = ["1", "2", "3"]
    impacts = []
    target_time = datetime.now(timezone.utc)

    for fid in facilities:
        meta = get_facility_metadata(fid)
        fac_lat = meta.get("latitude", 12.9716)
        fac_lon = meta.get("longitude", 77.5946)

        # Query database for actual capacity if available
        capacity = 100
        try:
            cap_stmt = (
                select(OccupancyHistory.total_slots)
                .where(OccupancyHistory.facility_id == fid)
                .order_by(OccupancyHistory.collected_at.desc())
                .limit(1)
            )
            cap_val = (await db.execute(cap_stmt)).scalar()
            if cap_val:
                capacity = cap_val
        except Exception:
            pass

        imp = EventImpactEngine.calculate_impact(
            event_type=ev.type,
            expected_attendance=ev.expected_attendance,
            start_time=ev.start_time,
            end_time=ev.end_time,
            confidence_score=ev.confidence_score,
            event_lat=ev.latitude,
            event_lon=ev.longitude,
            radius_of_influence=ev.radius_of_influence,
            facility_id=fid,
            facility_lat=fac_lat,
            facility_lon=fac_lon,
            facility_capacity=capacity,
            target_time=target_time,
            predicted_extra_demand_override=ev.predicted_extra_demand,
            congestion_multiplier_override=ev.congestion_multiplier,
        )
        if imp["extra_occupancy_percentage"] > 0.0 or imp["congestion_multiplier"] > 1.0:
            impacts.append(
                EventImpact(
                    event_id=ev.event_id,
                    facility_id=fid,
                    distance_km=imp["distance_km"],
                    attendance_impact=imp["attendance_impact"],
                    extra_occupancy_percentage=imp["extra_occupancy_percentage"],
                    expected_congestion_level=imp["expected_congestion_level"],
                    queue_wait_increase_minutes=imp["queue_wait_increase_minutes"],
                    facility_utilization_increase_percentage=imp["facility_utilization_increase_percentage"],
                    parking_demand_surge_multiplier=imp["parking_demand_surge_multiplier"],
                    travel_delay_minutes=imp["travel_delay_minutes"],
                )
            )

    return impacts
