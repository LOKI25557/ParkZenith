import logging
import math
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import APIRouter, Query, HTTPException, status, Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.session import get_async_session
from backend.app.models.parking import ParkingFacility, ParkingSlot
from backend.app.services.ai_service_client import ai_service_client
from backend.app.schemas.prediction import RecommendationRequestSchema
from backend.app.core.cache import cache

logger = logging.getLogger("backend.api.prediction")

router = APIRouter(prefix="/prediction", tags=["prediction"])


# Static registry for fallback metadata when AI Service is unavailable
FALLBACK_REGISTRY = {
    "1": {"name": "Downtown Central Parking", "lat": 12.9716, "lon": 77.5946, "rate": 20.0},
    "2": {"name": "City Mall Parking", "lat": 12.9750, "lon": 77.6000, "rate": 40.0},
    "FAC-001": {"name": "North Station Garage", "lat": 12.9800, "lon": 77.5900, "rate": 15.0},
}


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Simple Euclidean approximation for distance in kilometers."""
    return math.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2) * 111.0


async def db_fallback_occupancy(db: AsyncSession, facility_id: int) -> tuple[float, int, int]:
    """
    Computes current occupancy and slot counts directly from the backend DB.
    Returns: (occupancy_percentage, total_slots, occupied_slots)
    """
    try:
        total_slots_stmt = select(func.count(ParkingSlot.id)).where(ParkingSlot.facility_id == facility_id)
        occupied_slots_stmt = select(func.count(ParkingSlot.id)).where(
            and_(ParkingSlot.facility_id == facility_id, ParkingSlot.is_available == False)
        )
        
        total_res = await db.execute(total_slots_stmt)
        occupied_res = await db.execute(occupied_slots_stmt)
        
        total_slots = total_res.scalar() or 0
        occupied_slots = occupied_res.scalar() or 0
        current_occ = (occupied_slots / total_slots * 100.0) if total_slots > 0 else 0.0
        return current_occ, total_slots, occupied_slots
    except Exception as exc:
        logger.error("DB occupancy fallback calculation failed: %s", str(exc))
        return 0.0, 0, 0


def handle_client_response(res: dict):
    """
    Helper to extract data or raise appropriate HTTP exceptions based on client error codes.
    """
    if not res.get("success", False):
        err = res.get("error", {})
        code = err.get("code")
        message = err.get("message", "AI Service encountered an error.")
        status_code = err.get("status_code", 500)

        if code in ("AI_SERVICE_UNAVAILABLE", "AI_SERVICE_TIMEOUT", "MODEL_UNAVAILABLE", "AI_SERVICE_INVALID_RESPONSE"):
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=message)
        elif code in ("MISSING_FACILITY", "EMPTY_DATASET"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        elif code in ("INVALID_DATE_RANGE", "INSUFFICIENT_DATA", "DUPLICATE_DATA"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
        else:
            raise HTTPException(status_code=status_code, detail=message)
    return res.get("data")


@router.get("/ping")
async def ping_prediction():
    return {"message": "prediction service connected"}


@router.get("/occupancy/{facility_id}")
async def get_occupancy_forecast(
    facility_id: int,
    horizon_minutes: int = Query(15, ge=1, description="Horizon in minutes (15, 30, 60 or custom)"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Retrieves occupancy prediction forecasts. Falls back gracefully to DB slots occupancy if down.
    """
    cache_key = f"occ:{facility_id}:{horizon_minutes}"
    cached_val = cache.get(cache_key)
    if cached_val is not None:
        logger.info("Serving occupancy prediction from cache for facility %d", facility_id)
        return cached_val

    res = await ai_service_client.get_occupancy_prediction(facility_id, horizon_minutes)
    if not res.get("success", False):
        code = res.get("error", {}).get("code")
        if code in ("AI_SERVICE_UNAVAILABLE", "AI_SERVICE_TIMEOUT", "AI_SERVICE_DISABLED", "MODEL_UNAVAILABLE", "AI_SERVICE_INVALID_RESPONSE"):
            logger.warning("AI Service unavailable or malformed. Activating DB fallback for facility %d occupancy.", facility_id)
            current_occ, _, _ = await db_fallback_occupancy(db, facility_id)
            fallback_res = {
                "facility_id": facility_id,
                "current_occupancy": current_occ,
                "prediction_15": current_occ,
                "prediction_30": current_occ,
                "prediction_60": current_occ,
                "confidence": 0.0,
                "prediction_status": "DEGRADED_FALLBACK"
            }
            cache.set(cache_key, fallback_res, 10)
            return fallback_res

    res_data = handle_client_response(res)
    cache.set(cache_key, res_data, 60)
    return res_data


@router.get("/availability/{facility_id}")
async def get_availability_forecast(
    facility_id: str,
    eta_minutes: int = Query(20, ge=0, description="Estimated arrival time in minutes"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Retrieves availability prediction. Falls back gracefully to DB slots calculations if down.
    """
    cache_key = f"avail:{facility_id}:{eta_minutes}"
    cached_val = cache.get(cache_key)
    if cached_val is not None:
        logger.info("Serving availability prediction from cache for facility %s", facility_id)
        return cached_val

    res = await ai_service_client.get_availability_prediction(facility_id, eta_minutes)
    if not res.get("success", False):
        code = res.get("error", {}).get("code")
        if code in ("AI_SERVICE_UNAVAILABLE", "AI_SERVICE_TIMEOUT", "AI_SERVICE_DISABLED", "MODEL_UNAVAILABLE", "AI_SERVICE_INVALID_RESPONSE"):
            logger.warning("AI Service unavailable or malformed. Activating DB fallback for facility %s availability.", facility_id)
            fid = int(facility_id) if facility_id.isdigit() else 1
            current_occ, total_slots, occupied_slots = await db_fallback_occupancy(db, fid)
            expected_free = total_slots - occupied_slots
            prob = (expected_free / total_slots * 100.0) if total_slots > 0 else 0.0
            
            risk = "LOW"
            if current_occ >= 90.0:
                risk = "HIGH"
            elif current_occ >= 70.0:
                risk = "MEDIUM"

            fallback_res = {
                "facility_id": facility_id,
                "eta_minutes": eta_minutes,
                "current_occupancy": current_occ,
                "forecast_occupancy": current_occ,
                "expected_free_slots": expected_free,
                "availability_probability": prob,
                "occupancy_risk": risk,
                "confidence": 0.0,
                "prediction_status": "DEGRADED_FALLBACK",
                "availability_status": "HIGH_DEMAND" if risk == "HIGH" else ("LIMITED" if risk == "MEDIUM" else "AVAILABLE"),
                "risk_level": f"{risk}_RISK",
            }
            cache.set(cache_key, fallback_res, 10)
            return fallback_res

    res_data = handle_client_response(res)
    cache.set(cache_key, res_data, 60)
    return res_data


@router.post("/recommendations")
async def get_recommendations(req: RecommendationRequestSchema, db: AsyncSession = Depends(get_async_session)):
    """
    Query the Smart Recommendation Engine. Falls back to distance-based DB ranking if down.
    """
    cache_key = f"rec:{req.latitude}:{req.longitude}:{req.eta_minutes}:{req.max_distance_km}:{req.max_results}:{req.max_parking_fee}:{req.parking_type}:{req.accessibility_required}"
    cached_val = cache.get(cache_key)
    if cached_val is not None:
        logger.info("Serving recommendations from cache")
        return cached_val

    res = await ai_service_client.get_recommendations(
        latitude=req.latitude,
        longitude=req.longitude,
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
    if not res.get("success", False):
        code = res.get("error", {}).get("code")
        if code in ("AI_SERVICE_UNAVAILABLE", "AI_SERVICE_TIMEOUT", "AI_SERVICE_DISABLED", "MODEL_UNAVAILABLE"):
            logger.warning("AI Service unavailable. Activating DB distance fallback for recommendations.")
            # Retrieve active facilities from database
            stmt = select(ParkingFacility).where(ParkingFacility.is_active == True)
            facilities = (await db.execute(stmt)).scalars().all()
            
            results = []
            for f in facilities:
                fid_str = str(f.id)
                reg = FALLBACK_REGISTRY.get(fid_str, {
                    "name": f.name,
                    "lat": req.latitude + 0.01,
                    "lon": req.longitude + 0.01,
                    "rate": 20.0
                })
                
                dist = calculate_distance(req.latitude, req.longitude, reg["lat"], reg["lon"])
                if dist > req.max_distance_km:
                    continue
                    
                current_occ, total, occupied = await db_fallback_occupancy(db, f.id)
                free_slots = total - occupied
                prob = (free_slots / total * 100.0) if total > 0 else 0.0
                
                results.append({
                    "rank": 0,
                    "facility_id": fid_str,
                    "facility_name": f.name,
                    "recommendation_score": round(max(0.0, 100.0 - (dist * 12) - (current_occ * 0.25)), 2),
                    "availability_probability": prob,
                    "current_occupancy": current_occ,
                    "forecast_occupancy": current_occ,
                    "distance_km": round(dist, 2),
                    "walking_distance_m": int(dist * 1200),
                    "estimated_cost": reg["rate"],
                    "queue_wait_minutes": 0.0,
                    "occupancy_risk": "HIGH" if current_occ >= 90.0 else ("MEDIUM" if current_occ >= 70.0 else "LOW"),
                    "confidence": 0.0,
                    "reason": f"Fallback recommendation based on coordinates and current database slot usage. Distance {dist:.2f} km."
                })
                
            results.sort(key=lambda x: x["recommendation_score"], reverse=True)
            for idx, item in enumerate(results):
                item["rank"] = idx + 1
                
            fallback_res = {
                "recommendations": results[:req.max_results],
                "total_candidates": len(results),
                "returned_results": len(results[:req.max_results])
            }
            cache.set(cache_key, fallback_res, 10)
            return fallback_res

    res_data = handle_client_response(res)
    cache.set(cache_key, res_data, 60)
    return res_data


@router.get("/queue/{facility_id}")
async def get_queue_metrics(
    facility_id: str,
    eta_minutes: Optional[int] = Query(None, ge=0, description="Prediction horizon in minutes"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Retrieves queue metrics. Falls back gracefully to zero wait/length if down.
    """
    cache_key = f"queue:{facility_id}:{eta_minutes}"
    cached_val = cache.get(cache_key)
    if cached_val is not None:
        logger.info("Serving queue metrics from cache for facility %s", facility_id)
        return cached_val

    if eta_minutes is not None:
        res = await ai_service_client.get_queue_prediction(facility_id, eta_minutes)
    else:
        res = await ai_service_client.get_queue_status(facility_id)
        
    if not res.get("success", False):
        code = res.get("error", {}).get("code")
        if code in ("AI_SERVICE_UNAVAILABLE", "AI_SERVICE_TIMEOUT", "AI_SERVICE_DISABLED", "MODEL_UNAVAILABLE"):
            logger.warning("AI Service unavailable. Activating DB fallback for facility %s queue.", facility_id)
            fallback_res = {
                "facility_id": facility_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "current_queue_length": 0.0,
                "predicted_queue_length": 0.0,
                "expected_arrivals": 0.0,
                "expected_departures": 0.0,
                "expected_wait_minutes": 0.0,
                "estimated_wait_minutes": 0.0,
                "queue_trend": "STABLE",
                "congestion_level": "LOW",
                "congestion_status": "LOW",
                "confidence": 0.0,
                "prediction_status": "DEGRADED_FALLBACK"
            }
            cache.set(cache_key, fallback_res, 10)
            return fallback_res

    res_data = handle_client_response(res)
    cache.set(cache_key, res_data, 30)
    return res_data


@router.get("/decision/{facility_id}")
async def get_intelligence_decision(
    facility_id: str,
    eta_minutes: int = Query(20, ge=0, description="Estimated arrival time in minutes"),
    latitude: Optional[float] = Query(None, ge=-90.0, le=90.0),
    longitude: Optional[float] = Query(None, ge=-180.0, le=180.0),
    destination_latitude: Optional[float] = Query(None, ge=-90.0, le=90.0),
    destination_longitude: Optional[float] = Query(None, ge=-180.0, le=180.0),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Retrieve unified predictive intelligence decision from orchestrator, falling back gracefully to DB slot analysis if down.
    """
    cache_key = f"decision:{facility_id}:{eta_minutes}:{latitude}:{longitude}:{destination_latitude}:{destination_longitude}"
    cached_val = cache.get(cache_key)
    if cached_val is not None:
        logger.info("Serving unified decision from cache for facility %s", facility_id)
        return cached_val

    res = await ai_service_client.get_intelligence_decision(
        facility_id=facility_id,
        eta_minutes=eta_minutes,
        latitude=latitude,
        longitude=longitude,
        destination_latitude=destination_latitude,
        destination_longitude=destination_longitude,
    )
    if not res.get("success", False):
        code = res.get("error", {}).get("code")
        if code in ("AI_SERVICE_UNAVAILABLE", "AI_SERVICE_TIMEOUT", "AI_SERVICE_DISABLED", "MODEL_UNAVAILABLE"):
            logger.warning("AI Service unavailable. Activating DB fallback for unified decision on facility %s.", facility_id)
            
            fid = int(facility_id) if facility_id.isdigit() else 1
            current_occ, total_slots, occupied_slots = await db_fallback_occupancy(db, fid)
            expected_free = total_slots - occupied_slots
            prob = (expected_free / total_slots) if total_slots > 0 else 0.0
            
            recommendation = "GOOD_CHOICE"
            if current_occ >= 90.0 or prob < 0.3:
                recommendation = "UNLIKELY"
            elif current_occ >= 70.0 or prob < 0.7:
                recommendation = "LIMITED"
                
            reasoning = [
                "Current occupancy baseline used due to AI Service offline",
                "Calculated from real-time slot state in backend DB"
            ]
            if current_occ < 80.0:
                reasoning.append("Predicted occupancy remains below critical threshold")
            else:
                reasoning.append("High predicted occupancy at arrival")

            # Fallback alternatives search
            alt_stmt = select(ParkingFacility).where(and_(ParkingFacility.is_active == True, ParkingFacility.id != fid)).limit(3)
            alt_facs = (await db.execute(alt_stmt)).scalars().all()
            alternatives = []
            
            for af in alt_facs:
                a_occ, _, _ = await db_fallback_occupancy(db, af.id)
                alternatives.append({
                    "facility_id": str(af.id),
                    "score": round((100.0 - a_occ) / 100.0, 2)
                })

            fallback_res = {
                "facility_id": facility_id,
                "eta_minutes": eta_minutes,
                "predicted_occupancy": current_occ,
                "predicted_available_slots": expected_free,
                "availability_probability": round(prob, 2),
                "queue_wait_minutes": 0.0,
                "confidence": 0.0,
                "recommendation": recommendation,
                "alternative_facilities": alternatives,
                "reasoning": reasoning,
                "prediction_status": "DEGRADED_FALLBACK"
            }
            cache.set(cache_key, fallback_res, 10)
            return fallback_res

    res_data = handle_client_response(res)
    cache.set(cache_key, res_data, 60)
    return res_data


@router.get("/dashboard")
async def get_ai_dashboard(
    facility_id: Optional[str] = Query(None),
    zone_id: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    event_id: Optional[str] = Query(None),
    eta_minutes: int = Query(20, ge=0),
    latitude: Optional[float] = Query(None),
    longitude: Optional[float] = Query(None),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Retrieve consolidated AI analytics dashboard from AI service, falling back gracefully to DB slots occupancy if down.
    """
    cache_key = f"dashboard:{facility_id}:{zone_id}:{start_date}:{end_date}:{event_id}:{eta_minutes}:{latitude}:{longitude}"
    cached_val = cache.get(cache_key)
    if cached_val is not None:
        logger.info("Serving AI dashboard from cache")
        return cached_val

    res = await ai_service_client.get_ai_dashboard(
        facility_id=facility_id,
        zone_id=zone_id,
        start_date=start_date,
        end_date=end_date,
        event_id=event_id,
        eta_minutes=eta_minutes,
        latitude=latitude,
        longitude=longitude,
    )

    if not res.get("success", False):
        code = res.get("error", {}).get("code")
        if code in ("AI_SERVICE_UNAVAILABLE", "AI_SERVICE_TIMEOUT", "AI_SERVICE_DISABLED", "MODEL_UNAVAILABLE"):
            logger.warning("AI Service unavailable. Activating DB fallback for consolidated AI dashboard.")
            
            fid = int(facility_id) if (facility_id and facility_id.isdigit()) else 1
            current_occ, total_slots, occupied_slots = await db_fallback_occupancy(db, fid)
            expected_free = total_slots - occupied_slots
            
            fallback_res = {
                "occupancy": {
                    "facility_id": str(fid),
                    "current_occupancy": current_occ,
                    "total_capacity": total_slots,
                    "available_spaces": expected_free,
                    "occupied_spaces": occupied_slots,
                    "reserved_spaces": 0,
                    "utilization_percentage": current_occ,
                    "historical_occupancy": [],
                    "peak_occupancy": current_occ,
                    "peak_hours": [],
                    "occupancy_trends": {}
                },
                "forecast": {
                    "forecast_30m": current_occ,
                    "forecast_60m": current_occ,
                    "forecast_horizon": [],
                    "confidence": 0.0,
                    "expected_demand": current_occ,
                    "expected_occupancy": current_occ,
                    "peak_demand_window": None,
                    "event_adjusted_forecast": None
                },
                "availability": {
                    "arrival_availability_probability": round((expected_free / total_slots * 100.0) if total_slots > 0 else 100.0, 2),
                    "eta_minutes": eta_minutes,
                    "expected_occupancy_at_arrival": current_occ,
                    "available_capacity": expected_free,
                    "confidence": 0.0,
                    "risk_level": "MEDIUM" if current_occ >= 70.0 else "LOW"
                },
                "recommendations": {
                    "recommended_facilities": [],
                    "summary_insights": ["AI Service is offline. Showing real-time database fallback occupancy."]
                },
                "queue": {
                    "current_queue_estimate": 0,
                    "predicted_waiting_time": 0.0,
                    "congestion_level": "LOW",
                    "queue_growth": 0.0,
                    "peak_queue_period": None,
                    "event_adjusted_queue_prediction": None
                },
                "heatmap": {
                    "zone_congestion": [],
                    "most_congested_zones": [],
                    "least_congested_zones": [],
                    "peak_congestion_period": None,
                    "historical_comparison": {}
                },
                "events": {
                    "active_events": [],
                    "upcoming_events": [],
                    "event_impact": {},
                    "expected_demand_increase": 0.0,
                    "affected_facilities": [],
                    "congestion_risk": "LOW",
                    "event_adjusted_occupancy": current_occ,
                    "event_adjusted_queue_estimates": 0.0
                },
                "performance": {
                    "prediction_accuracy": 0.0,
                    "error_metrics": {},
                    "confidence": 0.0,
                    "forecast_performance": {},
                    "availability_prediction_performance": {},
                    "recommendation_performance": {},
                    "queue_prediction_performance": {}
                },
                "insights": [
                    {
                        "type": "system",
                        "severity": "WARNING",
                        "message": "AI Service is offline. Aggregated predictions are unavailable."
                    }
                ],
                "summary": {
                    "status": "WARNING",
                    "timestamp": datetime.now(timezone.utc),
                    "total_facilities_monitored": 1
                }
            }
            cache.set(cache_key, fallback_res, 10)
            return fallback_res

    res_data = handle_client_response(res)
    cache.set(cache_key, res_data, 30)
    return res_data
