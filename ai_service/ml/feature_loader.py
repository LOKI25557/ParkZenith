"""
Feature Loader module for ParkZenith Forecasting.
Handles loading the dataset, running preprocessing if missing, and extracting features/targets.
"""

import os
import logging
from typing import Tuple, List, Optional
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.settings import settings
from ..preprocessing.dataset_builder import DatasetBuilder

logger = logging.getLogger(__name__)


async def load_or_build_forecast_dataset(
    db_session: AsyncSession,
    export_path: Optional[str] = None
) -> pd.DataFrame:
    """
    Loads forecast_training.csv from disk.
    If the file does not exist, runs the preprocessing pipeline to generate it.
    """
    target_dir = os.path.abspath(export_path) if export_path else os.path.abspath(settings.EXPORT_PATH)
    file_path = os.path.join(target_dir, "forecast_training.csv")

    if not os.path.exists(file_path):
        logger.info("forecast_training.csv not found at %s. Triggering Preprocessing Pipeline...", file_path)
        builder = DatasetBuilder(export_dir=target_dir)
        # Note: we need to run build_and_export_datasets which runs with resample_freq="15min"
        # However, Phase 3 dataset_builder defaults to PreprocessingPipeline which builds resampled hourly.
        # To support 15m intervals dynamically, we configure the pipeline to resample at 15m intervals
        # Let's check: in pipeline.py/feature_service.py, we can pass frequency.
        # Since DatasetBuilder uses PreprocessingPipeline and build_forecast_dataset, let's make sure
        # we generate it with resample_freq="15min" in feature_service or we customize the resample freq.
        # In our Phase 3 build_forecast_dataset, it defaults to resample_freq="h". We can modify it to use "15min"!
        # Wait, let's check what the default output interval of dataset builder is: it calls feature_service.build_forecast_dataset(..., resample_freq="h")? No, let's view dataset_builder.py to see.
        await builder.build_and_export_datasets(db_session, export_path=target_dir)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Failed to generate dataset at {file_path}")

    # Explicitly use context manager to open and read
    with open(file_path, "r", encoding="utf-8") as f:
        df = pd.read_csv(f)
        
    logger.info("Successfully loaded dataset from %s. Row count: %d", file_path, len(df))
    return df


def prepare_features_and_targets(
    df: pd.DataFrame,
    horizon_minutes: int,
    resample_freq_minutes: int = 15
) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
    """
    Prepares features (X) and target (y) for a given forecasting horizon.
    Target is occupancy_percentage shifted backward by: horizon_minutes // resample_freq_minutes.
    Excludes non-feature/identifier columns.
    """
    df_feat = df.copy()
    
    # Sort chronologically per facility to make sure shifting is correct
    if "facility_id" in df_feat.columns and "timestamp" in df_feat.columns:
        df_feat = df_feat.sort_values(by=["facility_id", "timestamp"])
    elif "timestamp" in df_feat.columns:
        df_feat = df_feat.sort_values(by=["timestamp"])

    # Calculate steps to shift backward
    steps = horizon_minutes // resample_freq_minutes
    if steps <= 0:
        steps = 1

    # Shift occupancy_percentage backward per facility group to avoid leaking cross-facility data
    if "facility_id" in df_feat.columns:
        df_feat["target_occupancy"] = (
            df_feat.groupby("facility_id")["occupancy_percentage"]
            .shift(-steps)
        )
    else:
        df_feat["target_occupancy"] = df_feat["occupancy_percentage"].shift(-steps)

    # Drop last rows where target is NaN (missing future values)
    df_feat = df_feat.dropna(subset=["target_occupancy"])

    if len(df_feat) == 0:
        raise ValueError(
            f"Dataset has no records remaining after shifting target for horizon {horizon_minutes} minutes."
        )

    # Exclude non-feature columns
    non_features = [
        "id",
        "collected_at",
        "timestamp",
        "facility_id",
        "zone_id",
        "target_occupancy"
    ]
    
    feature_cols = [c for c in df_feat.columns if c not in non_features]
    
    # Also ensure we only select numerical feature columns
    X = df_feat[feature_cols].select_dtypes(include=["number"])
    final_feature_cols = list(X.columns)
    
    y = df_feat["target_occupancy"]
    
    logger.info(
        "Prepared X shape: %s, y shape: %s for horizon %d minutes (%d steps).",
        X.shape, y.shape, horizon_minutes, steps
    )
    return X, y, final_feature_cols
