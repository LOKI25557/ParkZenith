"""
Confidence module for arrival availability prediction.
Determines prediction reliability and confidence based on ETA duration, forecasting model accuracy, and data depth.
"""

import math
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def calculate_prediction_confidence(
    eta_minutes: int,
    forecasting_confidence: Optional[float] = None,
    historical_records_count: int = 100
) -> float:
    """
    Computes the prediction confidence percentage (0-100%).
    Factors:
    - ETA Duration: Confidence decays exponentially as ETA extends into the future.
    - Forecasting Model: Blends in the ML model's confidence if available, else applies a penalty.
    - Historical Data: Penalizes predictions if there are very few historical records.
    """
    # 1. Base confidence starts at 100.0
    base_confidence = 100.0

    # 2. ETA decay (exponential decay with 180 minutes half-life parameter)
    eta_decay = math.exp(-float(eta_minutes) / 180.0)

    # 3. ML forecasting model factor
    if forecasting_confidence is not None:
        # Scale model confidence (which is in 0-100 format) to 0-1
        model_factor = max(50.0, min(100.0, forecasting_confidence)) / 100.0
    else:
        # Fallback penalty if ML forecasting model is missing or not trained (fallback to flow-based rates)
        model_factor = 0.75

    # 4. Data sufficiency penalty
    # We prefer at least 30 historical records for calculation.
    if historical_records_count <= 0:
        data_factor = 0.1
    elif historical_records_count < 30:
        data_factor = 0.3 + 0.7 * (float(historical_records_count) / 30.0)
    else:
        data_factor = 1.0

    # 5. Combine factors
    confidence = base_confidence * eta_decay * model_factor * data_factor
    
    # Round and clamp
    confidence_percentage = round(confidence, 2)
    final_confidence = max(0.0, min(100.0, confidence_percentage))
    
    logger.debug(
        "Confidence components: ETA decay: %.2f, Model factor: %.2f, Data factor: %.2f. Final: %.2f%%",
        eta_decay, model_factor, data_factor, final_confidence
    )
    return final_confidence
