"""
AI Intelligence Orchestrator Service.
Combines forecasting, availability, queues, and analytics into a unified decision engine.
"""

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from ai_service.core.exceptions import MissingFacilityError, DatabaseError

from ai_service.services.forecasting_service import ForecastingService
from ai_service.services.availability_service import AvailabilityService
from ai_service.services.queue_service import QueueService
from ai_service.services.analytics_service import AnalyticsService
from ai_service.services.recommendation_service import RecommendationService

from ai_service.recommendation.weights import get_facility_metadata

logger = logging.getLogger(__name__)


class IntelligenceService:
    """
    Central orchestration service for the production AI intelligence pipeline.
    Produces deterministic, explainable unified decisions and identifies alternative facilities.
    """

    def __init__(
        self,
        forecasting_service: Optional[ForecastingService] = None,
        availability_service: Optional[AvailabilityService] = None,
        queue_service: Optional[QueueService] = None,
        analytics_service: Optional[AnalyticsService] = None,
        recommendation_service: Optional[RecommendationService] = None,
    ) -> None:
        self.forecasting_service = forecasting_service or ForecastingService()
        self.availability_service = availability_service or AvailabilityService(
            forecasting_service=self.forecasting_service
        )
        self.queue_service = queue_service or QueueService()
        self.analytics_service = analytics_service or AnalyticsService()
        self.recommendation_service = recommendation_service or RecommendationService(
            forecasting_service=self.forecasting_service,
            availability_service=self.availability_service,
            analytics_service=self.analytics_service,
            queue_service=self.queue_service,
        )

    async def get_decision(
        self,
        db: AsyncSession,
        facility_id: str,
        eta_minutes: int = 20,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        destination_latitude: Optional[float] = None,
        destination_longitude: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Gathers predictions, availability, and queues to return a unified parking recommendation decision.
        """
        logger.info("Intelligence Orchestrator: Generating unified decision for facility %s, ETA: %d mins", facility_id, eta_minutes)

        # 1. Validate facility exists in database
        try:
            await self.availability_service._validate_facility(db, facility_id)
        except MissingFacilityError as exc:
            logger.error("Facility validation failed in Intelligence Orchestrator: %s", str(exc))
            raise exc
        except Exception as exc:
            logger.error("Database error during facility validation: %s", str(exc))
            raise DatabaseError(message=f"Database error during facility validation: {str(exc)}") from exc

        # 2. Call Availability Service (handles forecasting, current occupied, incoming reservations)
        try:
            avail_pred = await self.availability_service.predict_facility_availability(db, facility_id, eta_minutes)
        except Exception as e:
            logger.error("Availability prediction failed in Intelligence Orchestrator: %s. Using default fallback.", str(e))
            # Fallback to degraded availability
            avail_pred = {
                "current_occupancy": 50.0,
                "forecast_occupancy": 50.0,
                "expected_free_slots": 50,
                "availability_probability": 50.0,
                "occupancy_risk": "MEDIUM",
                "confidence": 50.0,
            }

        # 3. Call Queue Service
        try:
            queue_pred = await self.queue_service.get_queue_prediction(db, facility_id, eta_minutes)
        except Exception as e:
            logger.error("Queue prediction failed in Intelligence Orchestrator: %s. Using default fallback.", str(e))
            queue_pred = {
                "expected_wait_minutes": 0.0,
                "congestion_level": "MODERATE",
            }

        predicted_occ = avail_pred.get("forecast_occupancy", 50.0)
        free_slots = avail_pred.get("expected_free_slots", 50)
        prob = avail_pred.get("availability_probability", 50.0) / 100.0  # map 0-100 to 0-1 decimal
        wait_time = queue_pred.get("expected_wait_minutes", 0.0)
        confidence = avail_pred.get("confidence", 80.0) / 100.0  # map 0-100 to 0-1 decimal
        risk = avail_pred.get("occupancy_risk", "MEDIUM")
        congestion = queue_pred.get("congestion_level", "MODERATE")

        # 4. Recommendation Classification
        # GOOD_CHOICE, LIMITED, HIGH_DEMAND, UNLIKELY, UNKNOWN
        if prob < 0.30:
            recommendation = "UNLIKELY"
        elif risk == "HIGH" or congestion in ("HIGH", "SEVERE"):
            recommendation = "HIGH_DEMAND"
        elif risk == "MEDIUM" or prob < 0.70 or congestion == "MODERATE":
            recommendation = "LIMITED"
        else:
            recommendation = "GOOD_CHOICE"

        # 5. Reasoning Generation
        reasoning = []
        if predicted_occ < 80.0:
            reasoning.append("Predicted occupancy remains below critical threshold")
        else:
            reasoning.append("High predicted occupancy at arrival")

        if wait_time < 5.0:
            reasoning.append("Low queue pressure")
        else:
            reasoning.append("Significant queue wait time predicted")

        if prob >= 0.70:
            reasoning.append("High probability of slot availability")
        else:
            reasoning.append("Limited slot availability predicted")

        # 6. Rank Alternatives if Risky or Unavailable
        alternatives = []
        if recommendation != "GOOD_CHOICE":
            logger.info("Facility %s is classified as %s. Identifying alternatives.", facility_id, recommendation)
            # Resolve latitude/longitude defaults if not passed
            if latitude is None or longitude is None:
                meta = get_facility_metadata(facility_id)
                lat = meta.get("latitude", 12.9716)
                lon = meta.get("longitude", 77.5946)
            else:
                lat = latitude
                lon = longitude

            try:
                rec_res = await self.recommendation_service.get_recommendations(
                    db=db,
                    user_latitude=lat,
                    user_longitude=lon,
                    eta_minutes=eta_minutes,
                    destination_latitude=destination_latitude,
                    destination_longitude=destination_longitude,
                    max_distance_km=5.0,
                    max_results=5,
                )
                for item in rec_res.get("recommendations", []):
                    # Exclude the current facility
                    if str(item["facility_id"]) != str(facility_id):
                        alternatives.append({
                            "facility_id": str(item["facility_id"]),
                            "score": round(item["recommendation_score"] / 100.0, 2)
                        })
            except Exception as e:
                logger.error("Alternative facilities search failed: %s", str(e))

        return {
            "facility_id": str(facility_id),
            "eta_minutes": eta_minutes,
            "predicted_occupancy": predicted_occ,
            "predicted_available_slots": free_slots,
            "availability_probability": round(prob, 2),
            "queue_wait_minutes": wait_time,
            "confidence": round(confidence, 2),
            "recommendation": recommendation,
            "alternative_facilities": alternatives,
            "reasoning": reasoning,
            "prediction_status": "SUCCESS"
        }
