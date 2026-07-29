"""
Normalization module for ParkZenith Preprocessing Pipeline.
Provides a configurable wrapper for scikit-learn scalers: StandardScaler, MinMaxScaler, RobustScaler, and Normalizer.
"""

import logging
from typing import List, Optional
import pandas as pd

try:
    from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler, Normalizer
except ImportError:
    # Fallback to avoid import errors before environment setup finishes
    StandardScaler = MinMaxScaler = RobustScaler = Normalizer = None

logger = logging.getLogger(__name__)


class ScalerWrapper:
    """
    Encapsulates a scikit-learn scaler and exposes convenient fits/transforms for Pandas DataFrames.
    """

    def __init__(self, strategy: str = "standard") -> None:
        self.strategy = strategy.lower().strip()
        self.scaler = self._init_scaler()
        self.fitted_columns: List[str] = []

    def _init_scaler(self):
        """Initializes the underlying scikit-learn scaler."""
        if StandardScaler is None:
            raise ImportError("scikit-learn is not installed in the current environment.")

        if self.strategy == "standard":
            return StandardScaler()
        elif self.strategy == "minmax":
            return MinMaxScaler()
        elif self.strategy == "robust":
            return RobustScaler()
        elif self.strategy == "normalizer":
            return Normalizer()
        else:
            logger.warning("Unknown scaling strategy '%s'. Defaulting to StandardScaler.", self.strategy)
            return StandardScaler()

    def fit(self, df: pd.DataFrame, columns: List[str]) -> "ScalerWrapper":
        """
        Fits the scaler on the specified columns.
        """
        if not columns:
            return self

        # Filter columns present in the DataFrame
        valid_cols = [c for c in columns if c in df.columns]
        if not valid_cols:
            logger.warning("No valid columns found for scaling fitting.")
            return self

        self.fitted_columns = valid_cols
        # Extract values as float to prevent scaling integer warnings or errors
        data = df[self.fitted_columns].astype(float)
        self.scaler.fit(data)
        logger.info("Fitted scaler of type %s on columns: %s", self.scaler.__class__.__name__, self.fitted_columns)
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transforms the fitted columns of the DataFrame.
        """
        if not self.fitted_columns:
            return df

        df_scaled = df.copy()
        missing_cols = [c for c in self.fitted_columns if c not in df_scaled.columns]
        if missing_cols:
            raise ValueError(f"Columns missing during transformation: {missing_cols}")

        data = df_scaled[self.fitted_columns].astype(float)
        scaled_values = self.scaler.transform(data)
        
        # Assign back scaled values
        df_scaled[self.fitted_columns] = scaled_values
        logger.info("Normalized columns: %s", self.fitted_columns)
        return df_scaled

    def fit_transform(self, df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
        """
        Fits the scaler and transforms the specified columns in one step.
        """
        self.fit(df, columns)
        return self.transform(df)
