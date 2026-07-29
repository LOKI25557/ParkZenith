"""
Forecasting facade module for ParkZenith Occupancy Forecasting.
Coordinates loading, saving, training, and predicting with models.
"""

import logging
from typing import Dict, Any, Optional
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from .persistence import load_forecasting_package, save_forecasting_package, DEFAULT_MODEL_PATH
from .training import train_and_persist_all_models, train_model_for_horizon
from .feature_loader import load_or_build_forecast_dataset
from .prediction import generate_forecast_prediction

logger = logging.getLogger(__name__)


class OccupancyForecaster:
    """
    Unified manager class for occupancy forecasting models.
    Supports on-disk persistence, dynamic custom horizon training, and prediction runs.
    """

    def __init__(self, model_path: str = DEFAULT_MODEL_PATH) -> None:
        self.model_path = model_path
        self._package: Optional[Dict[str, Any]] = None

    def load(self) -> bool:
        """
        Loads the model package from disk. Returns True if successful.
        """
        self._package = load_forecasting_package(self.model_path)
        return self._package is not None

    @property
    def is_loaded(self) -> bool:
        """
        Returns True if models are loaded in memory and ready.
        """
        return self._package is not None

    async def train_all(
        self,
        db_session: AsyncSession,
        export_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Runs model training for default horizons (15, 30, 60 minutes)
        and persists them to disk.
        """
        summary_metrics = await train_and_persist_all_models(
            db_session=db_session,
            export_path=export_path,
            file_path=self.model_path
        )
        # Reload package in memory
        self.load()
        return summary_metrics

    async def get_or_train_custom_horizon(
        self,
        db_session: AsyncSession,
        horizon_minutes: int,
        export_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Checks if a model is already trained for the custom horizon.
        If not, dynamically trains the model for this custom horizon,
        caches it in the active package, and persists the package to disk.
        """
        h_str = str(horizon_minutes)
        
        # If not loaded, try loading first
        if not self.is_loaded:
            self.load()

        # If package is still not loaded (e.g. no models trained yet), we must train the defaults first
        if not self.is_loaded:
            logger.info("No model package found. Training default models before custom horizon.")
            await self.train_all(db_session, export_path)

        # Check if custom horizon is already trained
        if self._package and h_str in self._package["models"]:
            logger.info("Custom horizon model for %d minutes already available in cache.", horizon_minutes)
            return {
                "best_model_name": self._package["best_model_names"][h_str],
                "metrics": self._package["metrics"][h_str]
            }

        # Train custom horizon dynamically
        logger.info("Custom horizon model for %d minutes not found. Starting dynamic training...", horizon_minutes)
        df = await load_or_build_forecast_dataset(db_session, export_path)
        res = await train_model_for_horizon(df, horizon_minutes)

        # Cache in memory
        if self._package:
            self._package["models"][h_str] = res["model"]
            self._package["features"][h_str] = res["feature_columns"]
            self._package["metrics"][h_str] = res["metrics"]
            self._package["best_model_names"][h_str] = res["best_model_name"]
            
            # Save updated package to disk
            save_forecasting_package(self._package, self.model_path)
            logger.info("Custom horizon model for %d minutes cached and saved.", horizon_minutes)

        return {
            "best_model_name": res["best_model_name"],
            "metrics": res["metrics"]
        }

    def predict(self, horizon_minutes: int, latest_features_df: pd.DataFrame) -> float:
        """
        Generates occupancy prediction for the given horizon.
        """
        if not self.is_loaded:
            raise RuntimeError("Forecasting models are not loaded. Call load() or train_all() first.")
        
        assert self._package is not None
        return generate_forecast_prediction(self._package, horizon_minutes, latest_features_df)

    def get_metrics(self) -> Dict[str, Any]:
        """
        Returns training metrics for all trained horizons.
        """
        if not self.is_loaded:
            return {}
        assert self._package is not None
        return self._package["metrics"]

    def get_best_model_names(self) -> Dict[str, str]:
        """
        Returns the selected best model names per horizon.
        """
        if not self.is_loaded:
            return {}
        assert self._package is not None
        return self._package["best_model_names"]
