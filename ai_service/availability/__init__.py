"""
Availability prediction module for ParkZenith.
Predicts arrival availability by combining historical flow rates, reservation trends, and ML forecasts.
"""

from .availability_engine import AvailabilityEngine
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

__all__ = [
    "AvailabilityEngine",
    "calculate_expected_free_slots",
    "calculate_availability_probability",
    "determine_occupancy_risk",
    "determine_prediction_reliability",
    "estimate_flow_occupancy_change",
    "calculate_reservation_impact",
    "predict_arrival_occupancy",
    "calculate_prediction_confidence",
]
