"""
Evaluation metrics calculations for ParkZenith Occupancy Forecasting.
"""

from typing import Dict
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def calculate_mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Calculates Mean Absolute Percentage Error (MAPE).
    Uses a small epsilon to avoid division by zero.
    """
    y_true_arr = np.array(y_true)
    y_pred_arr = np.array(y_pred)
    epsilon = 1e-5
    
    # Clip absolute true values below epsilon to avoid division by zero
    denominators = np.clip(np.abs(y_true_arr), epsilon, None)
    absolute_percentage_errors = np.abs((y_true_arr - y_pred_arr) / denominators)
    return float(np.mean(absolute_percentage_errors) * 100.0)


def evaluate_predictions(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """
    Calculates MAE, RMSE, R2, and MAPE for predictions.
    Returns metrics as a dictionary.
    """
    mae = mean_absolute_error(y_true, y_pred)
    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_true, y_pred)
    mape = calculate_mape(y_true, y_pred)
    
    # Deriving confidence score: 100 - MAPE clamped between 0 and 100
    confidence = max(0.0, min(100.0, 100.0 - mape))
    
    return {
        "mae": float(mae),
        "rmse": float(rmse),
        "r2_score": float(r2),
        "mape": float(mape),
        "confidence": float(confidence)
    }
