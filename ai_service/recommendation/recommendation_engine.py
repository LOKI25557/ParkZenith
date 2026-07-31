"""
Recommendation Engine orchestration module.
"""

import logging
from typing import Dict, Any, List, Optional
from .filters import filter_candidate_facilities, calculate_distance_km, estimate_walking_distance_m
from .scoring import RecommendationScorer
from .ranking import rank_facilities
from .explanation import generate_recommendation_reason
from .weights import WeightConfiguration

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    RecommendationEngine orchestrates the end-to-end recommendation workflow:
    filtering candidates, scoring each factor, combining scores with weights,
    ranking deterministically, and generating user-friendly rationales.
    """

    @staticmethod
    def recommend(
        candidates: List[Dict[str, Any]],
        user_latitude: float,
        user_longitude: float,
        destination_latitude: Optional[float],
        destination_longitude: Optional[float],
        max_distance_km: float,
        weights: Optional[WeightConfiguration] = None,
        parking_type: Optional[str] = None,
        accessibility_required: Optional[bool] = False,
        max_parking_fee: Optional[float] = None,
        max_results: int = 5,
    ) -> Dict[str, Any]:
        """
        Runs the recommendation pipeline on candidate facilities.
        """
        logger.info("Executing recommendation engine for %d candidates...", len(candidates))

        # 1. Filter candidates based on radius and parameters
        filtered_candidates = filter_candidate_facilities(
            facilities=candidates,
            user_latitude=user_latitude,
            user_longitude=user_longitude,
            max_distance_km=max_distance_km,
            parking_type=parking_type,
            accessibility_required=accessibility_required,
            max_parking_fee=max_parking_fee,
        )

        total_candidates = len(filtered_candidates)
        scorer = RecommendationScorer(weights=weights)

        scored_list: List[Dict[str, Any]] = []

        # 2. Score and explain each candidate
        for fac in filtered_candidates:
            fac_lat = fac.get("latitude")
            fac_lon = fac.get("longitude")

            # Calculate walking distance if destination is provided
            if destination_latitude is not None and destination_longitude is not None:
                walk_dist_km = calculate_distance_km(fac_lat, fac_lon, destination_latitude, destination_longitude)
                fac["walking_distance_m"] = estimate_walking_distance_m(walk_dist_km)
            else:
                # If no destination is provided, fallback to estimating based on user-to-facility distance
                dist_km = fac.get("distance_km", 0.0)
                fac["walking_distance_m"] = estimate_walking_distance_m(dist_km)

            # Calculate scores
            scores = scorer.calculate_scores(fac, max_distance_km)
            final_score = scorer.calculate_final_score(scores)

            # Generate reason
            reason = generate_recommendation_reason(scores)

            # Compile recommendation item
            item = {
                "facility_id": fac.get("facility_id"),
                "facility_name": fac.get("name", f"Facility {fac.get('facility_id')}"),
                "recommendation_score": final_score,
                "availability_probability": round(fac.get("availability_probability", 50.0), 1),
                "current_occupancy": round(fac.get("current_occupancy", 0.0), 1),
                "forecast_occupancy": round(fac.get("forecast_occupancy", 0.0), 1),
                "distance_km": round(fac.get("distance_km", 0.0), 2),
                "walking_distance_m": fac.get("walking_distance_m", 0),
                "estimated_cost": fac.get("hourly_rate") or fac.get("parking_cost") or 0.0,
                "queue_wait_minutes": fac.get("queue_wait_minutes") or 0.0,
                "occupancy_risk": fac.get("occupancy_risk", "LOW"),
                "confidence": round(fac.get("confidence", 80.0), 1),
                "reason": reason,
            }
            scored_list.append(item)

        # 3. Rank facilities deterministically
        ranked_list = rank_facilities(scored_list)

        # 4. Limit to max results
        results = ranked_list[:max_results]

        logger.info(
            "Recommendation complete. Candidates: %d, Scored: %d, Returned: %d",
            len(candidates),
            total_candidates,
            len(results),
        )

        return {
            "recommendations": results,
            "total_candidates": total_candidates,
            "returned_results": len(results),
        }
