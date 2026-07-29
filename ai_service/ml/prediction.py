"""
Inference module for ParkZenith Occupancy Forecasting.
Handles feature alignment and running regressor predictions.
"""

import logging
from typing import Dict, Any, List
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def generate_forecast_prediction(
    package_data: Dict[str, Any],
    horizon_minutes: int,
    latest_features_df: pd.DataFrame
) -> float:
    """
    Given a loaded model package, a target horizon in minutes, and a single-row
    DataFrame containing the latest engineered features, runs inference.
    
    Ensures input feature columns are aligned (existence, type, and order) 
    with the training feature set of the selected model.
    """
    h_str = str(horizon_minutes)
    
    if h_str not in package_data["models"]:
        raise ValueError(f"No trained model available for horizon {horizon_minutes} minutes.")

    model = package_data["models"][h_str]
    expected_cols: List[str] = package_data["features"][h_str]

    # Convert single row/DataFrame to ensure it has all expected features
    pred_df = latest_features_df.copy()
    
    # Add any missing expected columns with a default value of 0.0
    for col in expected_cols:
        if col not in pred_df.columns:
            pred_df[col] = 0.0

    # Retain and order columns to match the training feature set exactly
    X = pred_df[expected_cols]

    # Run inference
    prediction = model.predict(X)[0]
    
    # Target is occupancy percentage, clamp between 0.0% and 100.0%
    clamped_prediction = float(np.clip(prediction, 0.0, 100.0))
    
    logger.info(
        "Generated prediction for horizon %d min: %.2f%% (clamped from %.2f%%)",
        horizon_minutes, clamped_prediction, prediction
    )
    return clamped_prediction
