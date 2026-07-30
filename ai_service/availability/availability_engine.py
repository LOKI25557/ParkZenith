"""
Availability Engine coordinator for Phase 5.
Combines all prediction factors and computes final availability outputs.
"""

import logging
from typing import Dict, Any, Optional

from .calculator import (
    calculate_expected_free_slots,
    calculate_availability_probability,
    determine_occupancy_risk,
    determine_prediction_reliability,
)
from .estimator import (
    estimate_flow_occupancy_change,
    calculate_reservation_impact,
)
from .predictor import predict_arrival_occupancy
from .confidence import calculate_prediction_confidence

logger = logging.getLogger(__name__)


class AvailabilityEngine:
    """
    Availability Engine orchestrating occupancy estimation, reservation impact analysis,
    probability calculation, and prediction confidence rating.
    """

    @staticmethod
    def predict_availability(
        facility_id: Any,
        capacity: int,
        current_occupied: int,
        avg_arrivals_per_hour: float,
        avg_departures_per_hour: float,
        incoming_reservations: int,
        outgoing_reservations: int,
        forecast_occupancy_pct: Optional[float] = None,
        forecasting_confidence: Optional[float] = None,
        historical_records_count: int = 100,
        eta_minutes: int = 0,
    ) -> Dict[str, Any]:
        """
        Orchestrates prediction factors to determine occupancy and availability probability at ETA.
        """
        logger.info(
            "Running availability engine for facility_id: %s with ETA: %d mins",
            str(facility_id), eta_minutes
        )

        if capacity <= 0:
            return {
                "facility_id": facility_id,
                "eta_minutes": eta_minutes,
                "current_occupancy": 0.0,
                "forecast_occupancy": 0.0,
                "expected_free_slots": 0,
                "availability_probability": 0.0,
                "occupancy_risk": "HIGH",
                "confidence": 0.0,
                "prediction_reliability": "LOW",
            }

        # 1. Estimate flow-based occupancy changes
        net_flow_change = estimate_flow_occupancy_change(
            avg_arrivals_per_hour=avg_arrivals_per_hour,
            avg_departures_per_hour=avg_departures_per_hour,
            eta_minutes=eta_minutes
        )

        # 2. Calculate reservation impact
        res_impact = calculate_reservation_impact(
            incoming_reservations=incoming_reservations,
            outgoing_reservations=outgoing_reservations
        )

        # 3. Predict occupied slots at ETA
        expected_occupied_slots = predict_arrival_occupancy(
            capacity=capacity,
            current_occupied=current_occupied,
            net_flow_change=net_flow_change,
            reservation_impact=res_impact,
            forecast_occupancy_pct=forecast_occupancy_pct,
            eta_minutes=eta_minutes
        )

        # Calculate occupancy percentages
        current_occupancy_pct = round((float(current_occupied) / float(capacity)) * 100.0, 2)
        forecast_occupancy_pct_final = round((expected_occupied_slots / float(capacity)) * 100.0, 2)

        # 4. Calculate expected free slots
        expected_free_slots = calculate_expected_free_slots(
            capacity=capacity,
            expected_occupied=expected_occupied_slots
        )

        # 5. Calculate availability probability
        availability_probability = calculate_availability_probability(
            capacity=capacity,
            expected_occupied=expected_occupied_slots,
            eta_minutes=eta_minutes
        )

        # Probability full
        probability_full = 100.0 - availability_probability

        # 6. Determine risk and reliability
        occupancy_risk = determine_occupancy_risk(
            expected_occupancy_pct=forecast_occupancy_pct_final,
            probability_full=probability_full
        )

        confidence_score = calculate_prediction_confidence(
            eta_minutes=eta_minutes,
            forecasting_confidence=forecasting_confidence,
            historical_records_count=historical_records_count
        )

        reliability = determine_prediction_reliability(confidence_score)

        result = {
            "facility_id": facility_id,
            "eta_minutes": eta_minutes,
            "current_occupancy": current_occupancy_pct,
            "forecast_occupancy": forecast_occupancy_pct_final,
            "expected_free_slots": expected_free_slots,
            "availability_probability": availability_probability,
            "occupancy_risk": occupancy_risk,
            "confidence": confidence_score,
            "prediction_reliability": reliability
        }

        logger.info(
            "Availability Engine completed. Facility: %s, Prob: %.2f%%, Risk: %s, Confidence: %.2f%%",
            str(facility_id), availability_probability, occupancy_risk, confidence_score
        )
        return result
