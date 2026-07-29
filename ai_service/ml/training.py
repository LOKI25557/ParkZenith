"""
Training coordinator module for ParkZenith Forecasting.
Coordinates data loading, feature preparation, model training/selection, and package building.
"""

import logging
from typing import Dict, Any, List
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from .feature_loader import load_or_build_forecast_dataset, prepare_features_and_targets
from .model_selector import select_best_model
from .persistence import save_forecasting_package, load_forecasting_package, DEFAULT_MODEL_PATH

logger = logging.getLogger(__name__)


async def train_model_for_horizon(
    df: pd.DataFrame,
    horizon_minutes: int
) -> Dict[str, Any]:
    """
    Trains and selects the best model for a specific forecasting horizon.
    """
    logger.info("Training pipeline started for horizon: %d minutes", horizon_minutes)
    
    # 1. Prepare features and targets
    X, y, feature_cols = prepare_features_and_targets(df, horizon_minutes)
    
    # 2. Select best model
    best_model, best_name, all_metrics, best_metrics = select_best_model(X, y)
    
    logger.info("Training pipeline completed for horizon: %d minutes. Best model: %s", horizon_minutes, best_name)
    return {
        "model": best_model,
        "best_model_name": best_name,
        "feature_columns": feature_cols,
        "metrics": best_metrics,
        "all_metrics": all_metrics
    }


async def train_and_persist_all_models(
    db_session: AsyncSession,
    export_path: str = None,
    file_path: str = DEFAULT_MODEL_PATH
) -> Dict[str, Any]:
    """
    Loads training dataset, trains models for horizons (15, 30, 60 minutes),
    and saves them as a unified package to disk.
    """
    logger.info("Global model training started...")
    
    # 1. Load or build the base forecast dataset
    df = await load_or_build_forecast_dataset(db_session, export_path)
    
    horizons = [15, 30, 60]
    package_data = {
        "models": {},
        "features": {},
        "metrics": {},
        "best_model_names": {}
    }
    
    summary_metrics = {}

    for h in horizons:
        try:
            res = await train_model_for_horizon(df, h)
            h_str = str(h)
            package_data["models"][h_str] = res["model"]
            package_data["features"][h_str] = res["feature_columns"]
            package_data["metrics"][h_str] = res["metrics"]
            package_data["best_model_names"][h_str] = res["best_model_name"]
            summary_metrics[h_str] = res["metrics"]
        except Exception as e:
            logger.exception("Failed to train forecasting model for horizon %d: %s", h, str(e))
            raise e

    # Save the package atomically
    save_forecasting_package(package_data, file_path)
    logger.info("Global model training completed and saved successfully.")
    
    return summary_metrics
