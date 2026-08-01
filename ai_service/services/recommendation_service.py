"""
RecommendationService module coordinating candidate selection, forecast/availability retrieval,
utilization analysis, and scoring engine orchestration.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ai_service.core.exceptions import DatabaseError
from ai_service.models.occupancy import OccupancyHistory
from ai_service.services.forecasting_service import ForecastingService
from ai_service.services.availability_service import AvailabilityService
from ai_service.services.analytics_service import AnalyticsService
from ai_service.services.queue_service import QueueService

from ai_service.recommendation.weights import WeightConfiguration, get_facility_metadata
from ai_service.recommendation.recommendation_engine import RecommendationEngine
from ai_service.recommendation.filters import calculate_distance_km, estimate_walking_distance_m
from ai_service.recommendation.scoring import RecommendationScorer
from ai_service.recommendation.explanation import generate_recommendation_reason

logger = logging.getLogger(__name__)


class RecommendationService:
    """
    RecommendationService manages the collection of all candidate data,
    coordinates with existing analytical and predictive services (Phase 4 & 5),
    and triggers the recommendation engine scoring.
    """

    def __init__(
        self,
        forecasting_service: Optional[ForecastingService] = None,
        availability_service: Optional[AvailabilityService] = None,
        analytics_service: Optional[AnalyticsService] = None,
        queue_service: Optional[QueueService] = None,
    ) -> None:
        self.forecasting_service = forecasting_service or ForecastingService()
        self.availability_service = availability_service or AvailabilityService(
            forecasting_service=self.forecasting_service
        )
        self.analytics_service = analytics_service or AnalyticsService()
        self.queue_service = queue_service or QueueService()

    async def get_status(self) -> Dict[str, Any]:
        """
        Retrieves status of underlying forecasting and availability engines.
        """
        forecasting_status = self.forecasting_service.get_status()
        availability_status = await self.availability_service.get_status()

        f_ready = forecasting_status.get("status") == "READY"
        a_ready = availability_status.get("status") == "READY"

        status_state = "READY" if (f_ready and a_ready) else "DEGRADED"
        return {
            "status": status_state,
            "forecasting_service_ready": f_ready,
            "availability_service_ready": a_ready,
            "message": (
                "Recommendation Service is fully operational with ML Forecasting and Availability support."
                if status_state == "READY"
                else "Recommendation Service is operating in degraded mode due to unready dependencies."
            ),
        }

    async def get_recommendations(
        self,
        db: AsyncSession,
        user_latitude: float,
        user_longitude: float,
        eta_minutes: int,
        destination_latitude: Optional[float] = None,
        destination_longitude: Optional[float] = None,
        max_distance_km: float = 5.0,
        max_results: int = 5,
        max_parking_fee: Optional[float] = None,
        parking_type: Optional[str] = None,
        preferred_facility: Optional[str] = None,
        accessibility_required: bool = False,
        weights: Optional[WeightConfiguration] = None,
    ) -> Dict[str, Any]:
        """
        Gathers candidate facilities, filters, retrieves predictions/analytics concurrently,
        scores them, and ranks them.
        """
        logger.info(
            "Generating recommendations: User=(%f, %f), ETA=%d, MaxDist=%.2f km, Preferred=%s",
            user_latitude,
            user_longitude,
            eta_minutes,
            max_distance_km,
            preferred_facility,
        )

        # 1. Fetch all distinct facility IDs from OccupancyHistory table to find active candidate keys
        try:
            stmt = select(OccupancyHistory.facility_id).distinct()
            res = await db.execute(stmt)
            facility_ids = [str(fid) for fid in res.scalars().all()]
        except Exception as exc:
            raise DatabaseError(f"Failed to fetch unique facilities: {str(exc)}") from exc

        if not facility_ids:
            logger.warning("No facilities found in database.")
            return {
                "recommendations": [],
                "total_candidates": 0,
                "returned_results": 0,
            }

        # 2. Compile candidate metadata from registry (with fallbacks)
        candidates_raw: List[Dict[str, Any]] = []
        for fid in facility_ids:
            meta = get_facility_metadata(fid, user_latitude, user_longitude)
            # Make sure ID and capacity is merged correctly
            fac_item = meta.copy()
            fac_item["facility_id"] = fid
            
            # Fetch latest total slots capacity from database as priority
            try:
                cap_stmt = (
                    select(OccupancyHistory.total_slots)
                    .where(OccupancyHistory.facility_id == fid)
                    .order_by(OccupancyHistory.collected_at.desc())
                    .limit(1)
                )
                cap_res = (await db.execute(cap_stmt)).scalar()
                if cap_res:
                    fac_item["total_slots"] = cap_res
            except Exception:
                pass  # fallback to registry capacity

            candidates_raw.append(fac_item)

        # 3. Perform pre-filtering (removes inactive, invalid coordinates, capacity <=0, too far away, type/accessibility mismatch)
        # Note: If preferred_facility is requested, we bypass distance/cost/type filter for it
        pre_filtered: List[Dict[str, Any]] = []
        
        # If preferred_facility is specified, we check if it is active and exists
        for fac in candidates_raw:
            fid = fac.get("facility_id")
            if preferred_facility and str(fid) == str(preferred_facility):
                # Bypass normal filtering constraints for preferred facility
                fac_copy = fac.copy()
                # Compute distance
                fac_copy["distance_km"] = round(calculate_distance_km(user_latitude, user_longitude, fac.get("latitude"), fac.get("longitude")), 2)
                fac_copy["walking_distance_m"] = int(fac_copy["distance_km"] * 1200.0)
                pre_filtered.append(fac_copy)
                
        # Filter other facilities
        other_candidates = [f for f in candidates_raw if not (preferred_facility and str(f.get("facility_id")) == str(preferred_facility))]
        filtered_others = RecommendationEngine.recommend(
            candidates=other_candidates,
            user_latitude=user_latitude,
            user_longitude=user_longitude,
            destination_latitude=destination_latitude,
            destination_longitude=destination_longitude,
            max_distance_km=max_distance_km,
            weights=weights,
            parking_type=parking_type,
            accessibility_required=accessibility_required,
            max_parking_fee=max_parking_fee,
            max_results=len(other_candidates), # get all that match filters first
        ).get("recommendations", [])

        # Map back to matching candidates_raw formats (filtered_others contains already scored recommendation items,
        # but we need to fetch predictions and build them correctly).
        # Let's align on which ones passed the filters:
        passed_ids = {str(item["facility_id"]) for item in filtered_others}
        if preferred_facility:
            passed_ids.add(str(preferred_facility))

        candidates_to_query = [f for f in candidates_raw if str(f.get("facility_id")) in passed_ids]

        if not candidates_to_query:
            logger.info("No candidates passed the filtering stage.")
            return {
                "recommendations": [],
                "total_candidates": 0,
                "returned_results": 0,
            }

        # 4. Concurrently query Phase 4 (predictions) and Phase 5 (availability/occupancy) for candidates
        async def fetch_facility_data(fac: Dict[str, Any]) -> Dict[str, Any]:
            fid = fac["facility_id"]
            
            # Predict availability (covers current occupancy, forecast occupancy, availability probability, confidence, risk)
            try:
                avail_pred = await self.availability_service.predict_facility_availability(db, fid, eta_minutes)
            except Exception as e:
                logger.warning("Failed to fetch availability prediction for facility %s: %s. Using fallbacks.", fid, str(e))
                # Fallback prediction values
                latest_occ_pct = 50.0
                try:
                    latest_stmt = select(OccupancyHistory.occupancy_percentage).where(OccupancyHistory.facility_id == fid).order_by(OccupancyHistory.collected_at.desc()).limit(1)
                    latest_val = (await db.execute(latest_stmt)).scalar()
                    if latest_val is not None:
                        latest_occ_pct = latest_val
                except Exception:
                    pass

                avail_pred = {
                    "availability_probability": 100.0 - latest_occ_pct,
                    "current_occupancy": latest_occ_pct,
                    "forecast_occupancy": latest_occ_pct,
                    "occupancy_risk": "MEDIUM",
                    "confidence": 75.0,
                }

            # Fetch utilization analytics over last 30 days
            historical_util = 50.0
            try:
                overview = await self.analytics_service.get_overview(db, facility_id=fid)
                historical_util = overview.get("facility_utilization") or 50.0
            except Exception as e:
                logger.warning("Failed to fetch analytics utilization for facility %s: %s. Using default.", fid, str(e))

            # Fetch queue prediction
            queue_wait_minutes = fac.get("queue_wait_minutes") or 0.0
            try:
                queue_pred = await self.queue_service.get_queue_prediction(db, fid, eta_minutes)
                queue_wait_minutes = queue_pred.get("expected_wait_minutes") or 0.0
            except Exception as e:
                logger.warning("Failed to fetch queue prediction for facility %s: %s. Using fallback.", fid, str(e))

            # Merge predictions into facility metadata copy
            enriched_fac = fac.copy()
            enriched_fac.update({
                "availability_probability": avail_pred.get("availability_probability"),
                "current_occupancy": avail_pred.get("current_occupancy"),
                "forecast_occupancy": avail_pred.get("forecast_occupancy"),
                "occupancy_risk": avail_pred.get("occupancy_risk"),
                "confidence": avail_pred.get("confidence"),
                "historical_utilization": historical_util,
                "queue_wait_minutes": queue_wait_minutes,
            })
            return enriched_fac

        # Concurrent execution of async tasks
        enriched_candidates = await asyncio.gather(*(fetch_facility_data(c) for c in candidates_to_query))

        # 5. Run recommendation scoring and ranking on enriched candidates
        recommendation_results = RecommendationEngine.recommend(
            candidates=enriched_candidates,
            user_latitude=user_latitude,
            user_longitude=user_longitude,
            destination_latitude=destination_latitude,
            destination_longitude=destination_longitude,
            max_distance_km=max_distance_km,
            weights=weights,
            parking_type=parking_type,
            accessibility_required=accessibility_required,
            max_parking_fee=max_parking_fee,
            max_results=max_results,
        )

        return recommendation_results

    async def get_facility_recommendation_detail(
        self,
        db: AsyncSession,
        facility_id: str,
        user_latitude: float,
        user_longitude: float,
        eta_minutes: int,
        destination_latitude: Optional[float] = None,
        destination_longitude: Optional[float] = None,
        weights: Optional[WeightConfiguration] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves detailed score breakdown and explanation for a specific facility.
        """
        fid = str(facility_id)
        # Fetch metadata
        meta = get_facility_metadata(fid, user_latitude, user_longitude)
        fac_item = meta.copy()
        fac_item["facility_id"] = fid

        # Fetch latest total slots capacity from database as priority
        try:
            cap_stmt = (
                select(OccupancyHistory.total_slots)
                .where(OccupancyHistory.facility_id == fid)
                .order_by(OccupancyHistory.collected_at.desc())
                .limit(1)
            )
            cap_res = (await db.execute(cap_stmt)).scalar()
            if cap_res:
                fac_item["total_slots"] = cap_res
        except Exception:
            pass  # fallback to registry capacity

        # Predict availability
        try:
            avail_pred = await self.availability_service.predict_facility_availability(db, fid, eta_minutes)
        except Exception as e:
            logger.warning("Failed to fetch availability prediction for facility %s: %s. Using fallbacks.", fid, str(e))
            avail_pred = {
                "availability_probability": 50.0,
                "current_occupancy": 50.0,
                "forecast_occupancy": 50.0,
                "occupancy_risk": "LOW",
                "confidence": 80.0,
            }

        # Fetch utilization
        historical_util = 50.0
        try:
            overview = await self.analytics_service.get_overview(db, facility_id=fid)
            historical_util = overview.get("facility_utilization") or 50.0
        except Exception as e:
            logger.warning("Failed to fetch analytics utilization for facility %s: %s.", fid, str(e))

        # Fetch queue prediction
        queue_wait_minutes = fac_item.get("queue_wait_minutes") or 0.0
        try:
            queue_pred = await self.queue_service.get_queue_prediction(db, fid, eta_minutes)
            queue_wait_minutes = queue_pred.get("expected_wait_minutes") or 0.0
        except Exception as e:
            logger.warning("Failed to fetch queue prediction for facility %s: %s. Using fallback.", fid, str(e))

        # Enrich
        fac_item.update({
            "availability_probability": avail_pred.get("availability_probability"),
            "current_occupancy": avail_pred.get("current_occupancy"),
            "forecast_occupancy": avail_pred.get("forecast_occupancy"),
            "occupancy_risk": avail_pred.get("occupancy_risk"),
            "confidence": avail_pred.get("confidence"),
            "historical_utilization": historical_util,
            "distance_km": round(calculate_distance_km(user_latitude, user_longitude, fac_item["latitude"], fac_item["longitude"]), 2),
            "queue_wait_minutes": queue_wait_minutes,
        })

        if destination_latitude is not None and destination_longitude is not None:
            walk_dist_km = calculate_distance_km(fac_item["latitude"], fac_item["longitude"], destination_latitude, destination_longitude)
            fac_item["walking_distance_m"] = estimate_walking_distance_m(walk_dist_km)
        else:
            fac_item["walking_distance_m"] = estimate_walking_distance_m(fac_item["distance_km"])

        # Calculate scores
        max_dist_limit = max(5.0, fac_item["distance_km"] * 1.5)
        scorer = RecommendationScorer(weights=weights)
        scores = scorer.calculate_scores(fac_item, max_dist_limit)
        final_score = scorer.calculate_final_score(scores)
        reason = generate_recommendation_reason(scores)

        return {
            "rank": 1,
            "facility_id": fid,
            "facility_name": fac_item.get("name", f"Facility {fid}"),
            "recommendation_score": final_score,
            "availability_probability": round(fac_item["availability_probability"], 1),
            "current_occupancy": round(fac_item["current_occupancy"], 1),
            "forecast_occupancy": round(fac_item["forecast_occupancy"], 1),
            "distance_km": fac_item["distance_km"],
            "walking_distance_m": fac_item["walking_distance_m"],
            "estimated_cost": fac_item.get("hourly_rate", 0.0),
            "queue_wait_minutes": fac_item.get("queue_wait_minutes", 0.0),
            "occupancy_risk": fac_item.get("occupancy_risk", "LOW"),
            "confidence": round(fac_item["confidence"], 1),
            "reason": reason,
        }
