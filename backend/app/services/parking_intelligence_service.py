import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from backend.app.models.parking_facility import ParkingFacility
from backend.app.services.parking_service import parking_service
from backend.app.services.ai_service_client import ai_service_client
from backend.app.api.prediction.router import db_fallback_occupancy, calculate_distance, FALLBACK_REGISTRY
from backend.app.schemas.unified import UnifiedFacilityIntelligence, UnifiedRecommendationResponse, EnrichedRecommendation
from backend.app.schemas.prediction import RecommendationRequestSchema
from backend.app.schemas.parking import AvailabilityResponse

logger = logging.getLogger("backend.services.parking_intelligence")

class ParkingIntelligenceService:
    async def get_facility_intelligence(
        self, db: AsyncSession, facility_id: int, eta_minutes: int = 20
    ) -> UnifiedFacilityIntelligence:
        """
        Aggregates real-time DB parking state with AI predictions for a unified view.
        """
        # 1. Authoritative Real-Time DB State
        try:
            availability: AvailabilityResponse = await parking_service.get_facility_availability(db, facility_id)
        except Exception as e:
            # Re-raise HTTP exceptions (like 404 Not Found)
            raise e

        # 2. AI Intelligence (Decision)
        facility_id_str = str(facility_id)
        decision_res = await ai_service_client.get_intelligence_decision(
            facility_id=facility_id_str,
            eta_minutes=eta_minutes
        )

        queue_res = await ai_service_client.get_queue_prediction(
            facility_id=facility_id_str,
            eta_minutes=eta_minutes
        )

        # 3. Handle AI Response & Fallbacks
        predicted_occupancy = None
        predicted_availability_prob = None
        expected_free_slots = None
        recommendation = None
        reasoning = []
        prediction_status = "OK"
        occupancy_risk = None
        queue_wait_minutes = None

        if decision_res.get("success", False):
            data = decision_res.get("data", {})
            predicted_occupancy = data.get("predicted_occupancy")
            predicted_availability_prob = data.get("availability_probability")
            expected_free_slots = data.get("predicted_available_slots")
            recommendation = data.get("recommendation")
            reasoning = data.get("reasoning", [])
            prediction_status = data.get("prediction_status", "OK")
            # Risk from AI might need to be parsed or mapped
            occupancy_risk = "HIGH" if (predicted_occupancy and predicted_occupancy >= 90) else "MEDIUM" if (predicted_occupancy and predicted_occupancy >= 70) else "LOW"
        else:
            prediction_status = "DEGRADED_FALLBACK"
            # DB Fallback for predictions
            current_occ, total, occupied = await db_fallback_occupancy(db, facility_id)
            expected_free = total - occupied
            predicted_occupancy = current_occ
            predicted_availability_prob = (expected_free / total) if total > 0 else 0.0
            expected_free_slots = expected_free
            
            recommendation = "GOOD_CHOICE"
            if current_occ >= 90.0 or predicted_availability_prob < 0.3:
                recommendation = "UNLIKELY"
            elif current_occ >= 70.0 or predicted_availability_prob < 0.7:
                recommendation = "LIMITED"
            
            occupancy_risk = "HIGH" if current_occ >= 90.0 else "MEDIUM" if current_occ >= 70.0 else "LOW"
            reasoning = ["AI Service is offline. Using real-time DB fallback for predictions."]

        if queue_res.get("success", False):
            q_data = queue_res.get("data", {})
            queue_wait_minutes = q_data.get("expected_wait_minutes") or q_data.get("estimated_wait_minutes", 0.0)
        else:
            queue_wait_minutes = 0.0

        return UnifiedFacilityIntelligence(
            facility_id=facility_id,
            total_slots=availability.total_slots,
            available_slots=availability.available,
            occupied_slots=availability.occupied,
            reserved_slots=availability.reserved,
            current_occupancy_percentage=availability.occupancy_percentage,
            predicted_occupancy_percentage=predicted_occupancy,
            predicted_availability_probability=predicted_availability_prob,
            expected_free_slots=expected_free_slots,
            queue_wait_minutes=queue_wait_minutes,
            recommendation=recommendation,
            occupancy_risk=occupancy_risk,
            prediction_status=prediction_status,
            reasoning=reasoning
        )

    async def get_enriched_recommendations(
        self, db: AsyncSession, req: RecommendationRequestSchema
    ) -> UnifiedRecommendationResponse:
        """
        Gets AI recommendations and enriches them with authoritative real-time DB availability.
        """
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

        candidates = []
        is_fallback = False

        if res.get("success", False):
            data = res.get("data", {})
            candidates = data.get("recommendations", [])
        else:
            is_fallback = True
            logger.warning("AI Recommendation failed. Activating DB distance fallback.")
            stmt = select(ParkingFacility).where(ParkingFacility.is_active == True)
            facilities = (await db.execute(stmt)).scalars().all()
            
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
                
                candidates.append({
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
            candidates.sort(key=lambda x: x["recommendation_score"], reverse=True)
            candidates = candidates[:req.max_results]
            for idx, item in enumerate(candidates):
                item["rank"] = idx + 1

        enriched_candidates = []
        for c in candidates:
            fac_id_str = c.get("facility_id")
            fac_id = int(fac_id_str) if str(fac_id_str).isdigit() else None
            
            actual_avail = 0
            actual_occ = 0.0

            if fac_id:
                try:
                    availability = await parking_service.get_facility_availability(db, fac_id)
                    actual_avail = availability.available
                    actual_occ = availability.occupancy_percentage
                except Exception:
                    # facility might not exist in DB but exists in mock registry
                    pass

            enriched_candidates.append(EnrichedRecommendation(
                rank=c.get("rank", 0),
                facility_id=fac_id_str,
                facility_name=c.get("facility_name", "Unknown"),
                recommendation_score=c.get("recommendation_score", 0.0),
                actual_available_slots=actual_avail,
                actual_occupancy_percentage=actual_occ,
                availability_probability=c.get("availability_probability", 0.0),
                forecast_occupancy=c.get("forecast_occupancy", 0.0),
                distance_km=c.get("distance_km", 0.0),
                walking_distance_m=c.get("walking_distance_m", 0),
                estimated_cost=c.get("estimated_cost", 0.0),
                queue_wait_minutes=c.get("queue_wait_minutes", 0.0),
                occupancy_risk=c.get("occupancy_risk", "LOW"),
                confidence=c.get("confidence", 0.0),
                reason=c.get("reason", "")
            ))

        return UnifiedRecommendationResponse(
            recommendations=enriched_candidates,
            total_candidates=len(enriched_candidates), # accurate only for returned count
            returned_results=len(enriched_candidates)
        )

parking_intelligence_service = ParkingIntelligenceService()
