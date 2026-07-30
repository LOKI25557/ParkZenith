"""
Calculations module for arrival availability prediction.
Implements statistical and mathematical formulas for occupancy probability, risk, and reliability.
"""

import math
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def calculate_expected_free_slots(capacity: int, expected_occupied: float) -> int:
    """
    Calculates expected free slots at ETA, ensuring value is at least 0 and at most capacity.
    """
    free_slots = int(round(max(0.0, float(capacity) - expected_occupied)))
    return min(capacity, free_slots)


def calculate_availability_probability(
    capacity: int,
    expected_occupied: float,
    eta_minutes: int
) -> float:
    """
    Calculates the probability (0-100%) that a space will be available at ETA.
    Uses normal cumulative distribution function (CDF) for occupancy approximation.
    """
    if capacity <= 0:
        return 0.0

    # Estimate uncertainty (standard deviation) based on capacity and ETA.
    # Uncertainty scales with capacity and grows with the square root of time (diffusion).
    time_factor = math.sqrt(eta_minutes / 60.0) if eta_minutes > 0 else 0.0
    sigma = max(1.5, float(capacity) * (0.03 + 0.06 * time_factor))

    # Calculate probability that occupied slots < capacity (with continuity correction of -0.5)
    limit = float(capacity) - 0.5
    z_score = (limit - expected_occupied) / sigma

    # Standard normal CDF formula
    probability = 0.5 * (1.0 + math.erf(z_score / math.sqrt(2.0)))
    
    # Scale to percentage and clamp between 0.0% and 100.0%
    probability_percentage = round(float(probability) * 100.0, 2)
    return max(0.0, min(100.0, probability_percentage))


def determine_occupancy_risk(expected_occupancy_pct: float, probability_full: float) -> str:
    """
    Categorizes the risk of the parking facility being full at arrival:
    - HIGH: Forecast occupancy >= 90% OR probability full >= 70%
    - MEDIUM: Forecast occupancy between 70% and 90% OR probability full between 20% and 70%
    - LOW: Otherwise
    """
    if expected_occupancy_pct >= 90.0 or probability_full >= 70.0:
        return "HIGH"
    elif expected_occupancy_pct >= 70.0 or probability_full >= 20.0:
        return "MEDIUM"
    else:
        return "LOW"


def determine_prediction_reliability(confidence_score: float) -> str:
    """
    Qualitatively grades prediction confidence score:
    - HIGH: Confidence >= 85.0
    - MEDIUM: 70.0 <= Confidence < 85.0
    - LOW: Confidence < 70.0
    """
    if confidence_score >= 85.0:
        return "HIGH"
    elif confidence_score >= 70.0:
        return "MEDIUM"
    else:
        return "LOW"
