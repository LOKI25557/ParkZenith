"""
Predictor module for arrival availability prediction.
Combines current occupancy, flow rates, reservation changes, and ML forecasting predictions using a temporal blend.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def predict_arrival_occupancy(
    capacity: int,
    current_occupied: int,
    net_flow_change: float,
    reservation_impact: int,
    forecast_occupancy_pct: Optional[float] = None,
    eta_minutes: int = 0
) -> float:
    """
    Predicts the expected number of occupied slots at ETA by blending flow-based dynamics and ML forecasting.
    
    Blending weights:
    - At ETA = 0, weight is 100% on current occupancy.
    - At ETA < 60 mins, blends flow-based (current + flow + reservations) and ML forecast.
    - At ETA >= 60 mins, relies heavily on ML forecast if available.
    - If ML forecast is missing, falls back 100% to flow-based calculation.
    """
    if capacity <= 0:
        return 0.0

    # 1. Flow-based prediction: current occupied slots plus net flow and reservation changes
    flow_occupied = float(current_occupied) + net_flow_change + float(reservation_impact)
    flow_occupied = max(0.0, min(float(capacity), flow_occupied))

    # 2. If forecast is available, calculate ML forecasted slots
    if forecast_occupancy_pct is not None:
        forecast_occupied = (forecast_occupancy_pct / 100.0) * float(capacity)
        forecast_occupied = max(0.0, min(float(capacity), forecast_occupied))

        # 3. Dynamic blending weight based on ETA (interpolating from 0 to 60 mins)
        # For short horizons, rely on flow. For longer horizons, rely on ML forecast.
        weight_ml = min(1.0, float(eta_minutes) / 60.0)
        expected_occupied = (1.0 - weight_ml) * flow_occupied + weight_ml * forecast_occupied
        
        logger.debug(
            "Blended prediction: Flow=%.2f, ML=%.2f, WeightML=%.2f. Blended: %.2f",
            flow_occupied, forecast_occupied, weight_ml, expected_occupied
        )
    else:
        # Fallback to flow-based prediction only
        expected_occupied = flow_occupied
        logger.debug(
            "No ML forecast available. Falling back to Flow-based: %.2f",
            expected_occupied
        )

    # Final clamping
    return max(0.0, min(float(capacity), expected_occupied))
