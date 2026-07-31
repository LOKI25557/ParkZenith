"""
Scoring engine module for calculating normalized scores and final recommendation scores.
"""

import logging
from typing import Dict, Any, Optional
from .weights import WeightConfiguration

logger = logging.getLogger(__name__)


class RecommendationScorer:
    """
    RecommendationScorer handles normalization of different scoring factors
    and calculates the final weighted recommendation score.
    """

    def __init__(self, weights: Optional[WeightConfiguration] = None) -> None:
        self.weights = weights or WeightConfiguration()

    def normalize_availability(self, availability_prob: Optional[float]) -> float:
        """
        Availability Probability is already 0-100. Higher is better.
        """
        if availability_prob is None:
            return 50.0  # Neutral fallback
        return min(max(float(availability_prob), 0.0), 100.0)

    def normalize_occupancy(self, current_occ_pct: Optional[float]) -> float:
        """
        Lower current occupancy percentage is better.
        """
        if current_occ_pct is None:
            return 50.0  # Neutral fallback
        val = min(max(float(current_occ_pct), 0.0), 100.0)
        return 100.0 - val

    def normalize_forecast(self, forecast_occ_pct: Optional[float]) -> float:
        """
        Lower forecasted occupancy percentage is better.
        """
        if forecast_occ_pct is None:
            return 50.0  # Neutral fallback
        val = min(max(float(forecast_occ_pct), 0.0), 100.0)
        return 100.0 - val

    def normalize_distance(self, distance_km: Optional[float], max_distance_km: float) -> float:
        """
        Closer distance is better.
        If distance is 0, score is 100. If distance >= max_distance_km, score is 0.
        """
        if distance_km is None:
            return 50.0  # Neutral fallback
        dist = float(distance_km)
        if max_distance_km <= 0:
            return 100.0
        score = 100.0 * (1.0 - (dist / max_distance_km))
        return min(max(score, 0.0), 100.0)

    def normalize_walking_distance(self, walking_distance_m: Optional[float], max_walking_m: float = 1000.0) -> float:
        """
        Shorter walking distance is better.
        If walking_distance is 0, score is 100. If walking_distance >= max_walking_m, score is 0.
        """
        if walking_distance_m is None:
            return 50.0
        w_dist = float(walking_distance_m)
        if max_walking_m <= 0:
            return 100.0
        score = 100.0 * (1.0 - (w_dist / max_walking_m))
        return min(max(score, 0.0), 100.0)

    def normalize_cost(self, cost: Optional[float], max_cost: float = 50.0) -> float:
        """
        Lower cost is better.
        If cost is 0, score is 100. If cost >= max_cost, score is 0.
        """
        if cost is None:
            return 50.0
        c = float(cost)
        if c <= 0.0:
            return 100.0
        if max_cost <= 0:
            return 0.0
        score = 100.0 * (1.0 - (c / max_cost))
        return min(max(score, 0.0), 100.0)

    def normalize_utilization(self, utilization: Optional[float]) -> float:
        """
        Uses historical utilization intelligently.
        Avoids automatically treating high utilization as always good or always bad.
        Treats 60% as the optimal demand/reliability sweet spot.
        """
        if utilization is None:
            return 75.0  # Neutral-high fallback since we assume average demand
        u = min(max(float(utilization), 0.0), 100.0)
        # Optimal utilization target is 60%. Deviation reduces score.
        deviation = abs(u - 60.0)
        score = 100.0 - (deviation * 2.0)
        return min(max(score, 0.0), 100.0)

    def normalize_queue(self, wait_minutes: Optional[float], max_wait: float = 15.0) -> float:
        """
        Lower queue/congestion wait time is better.
        If wait is 0, score is 100. If wait >= max_wait, score is 0.
        """
        if wait_minutes is None:
            return 100.0  # If no queue data is available, assume no congestion (excellent score)
        w = float(wait_minutes)
        if w <= 0.0:
            return 100.0
        if max_wait <= 0:
            return 0.0
        score = 100.0 * (1.0 - (w / max_wait))
        return min(max(score, 0.0), 100.0)

    def calculate_scores(self, data: Dict[str, Any], max_distance_km: float) -> Dict[str, float]:
        """
        Calculates all individual normalized scores.
        """
        # Fallbacks for missing data in the input dict
        availability_prob = data.get("availability_probability")
        current_occ = data.get("current_occupancy")
        forecast_occ = data.get("forecast_occupancy")
        distance_km = data.get("distance_km")
        walking_distance_m = data.get("walking_distance_m")
        parking_cost = data.get("hourly_rate") or data.get("parking_cost") or data.get("estimated_cost")
        utilization = data.get("historical_utilization")
        queue_wait = data.get("queue_wait_minutes")

        # Resolve inter-factor fallbacks
        if current_occ is None:
            # Try to calculate from total/occupied slots
            total_slots = data.get("total_slots", 0)
            occupied_slots = data.get("occupied_slots", 0)
            if total_slots > 0:
                current_occ = (occupied_slots / total_slots) * 100.0

        if availability_prob is None and current_occ is not None:
            availability_prob = 100.0 - current_occ

        if forecast_occ is None:
            forecast_occ = current_occ

        if walking_distance_m is None and distance_km is not None:
            walking_distance_m = distance_km * 1200.0  # multiplier = 1.2

        max_walking_m = max(1000.0, max_distance_km * 1200.0)

        # Normalize individual scores
        scores = {
            "availability_score": self.normalize_availability(availability_prob),
            "distance_score": self.normalize_distance(distance_km, max_distance_km),
            "forecast_score": self.normalize_forecast(forecast_occ),
            "occupancy_score": self.normalize_occupancy(current_occ),
            "walking_score": self.normalize_walking_distance(walking_distance_m, max_walking_m),
            "utilization_score": self.normalize_utilization(utilization),
            "cost_score": self.normalize_cost(parking_cost),
            "queue_score": self.normalize_queue(queue_wait),
        }
        return scores

    def calculate_final_score(self, scores: Dict[str, float]) -> float:
        """
        Combines individual normalized scores using configured weights.
        Returns a final score between 0.0 and 100.0.
        """
        final_score = (
            scores["availability_score"] * self.weights.availability_probability
            + scores["distance_score"] * self.weights.distance
            + scores["forecast_score"] * self.weights.forecast_occupancy
            + scores["occupancy_score"] * self.weights.current_occupancy
            + scores["walking_score"] * self.weights.walking_distance
            + scores["utilization_score"] * self.weights.historical_utilization
            + scores["cost_score"] * self.weights.parking_cost
            + scores["queue_score"] * self.weights.queue_congestion
        )
        return round(min(max(final_score, 0.0), 100.0), 2)
