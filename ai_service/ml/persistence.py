"""
Model Persistence module for ParkZenith Forecasting.
Handles atomic saving and loading of the model packages and metrics using joblib.
"""

import os
import tempfile
import logging
from typing import Dict, Any, Optional
import joblib

logger = logging.getLogger(__name__)

DEFAULT_MODEL_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "models",
        "occupancy_forecast.joblib"
    )
)


def save_forecasting_package(
    package_data: Dict[str, Any],
    file_path: str = DEFAULT_MODEL_PATH
) -> None:
    """
    Saves the entire forecasting model package (models, features, metrics) atomically.
    Overwrites the previous file safely by writing to a temporary file first, then renaming.
    """
    target_dir = os.path.dirname(file_path)
    os.makedirs(target_dir, exist_ok=True)

    # Atomic save: write to temp file first, then rename
    fd, temp_path = tempfile.mkstemp(dir=target_dir, suffix=".tmp")
    os.close(fd)
    
    try:
        logger.info("Saving forecasting model package to temporary path: %s", temp_path)
        joblib.dump(package_data, temp_path)
        
        # Atomically replace target file
        if os.path.exists(file_path):
            os.remove(file_path)
        os.rename(temp_path, file_path)
        logger.info("Atomic save completed. Model package saved to: %s", file_path)
    except Exception as e:
        logger.error("Failed to save forecasting model package: %s", str(e))
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise e


def load_forecasting_package(
    file_path: str = DEFAULT_MODEL_PATH
) -> Optional[Dict[str, Any]]:
    """
    Loads and returns the forecasting model package if available.
    Returns None if the file is missing or invalid.
    """
    if not os.path.exists(file_path):
        logger.warning("No model package found at path: %s", file_path)
        return None

    try:
        logger.info("Loading forecasting model package from: %s", file_path)
        package_data = joblib.load(file_path)
        
        # Verify package structure
        required_keys = ["models", "features", "metrics", "best_model_names"]
        if not all(k in package_data for k in required_keys):
            logger.error("Loaded package at %s is corrupted or missing required keys.", file_path)
            return None

        logger.info("Successfully loaded model package with horizons: %s", list(package_data["models"].keys()))
        return package_data
    except Exception as e:
        logger.error("Error occurred while loading model package from %s: %s", file_path, str(e))
        return None
