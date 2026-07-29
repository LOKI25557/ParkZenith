"""
Preprocessing Pipeline module for ParkZenith Preprocessing Pipeline.
Coordinates loading, cleaning, validating, feature engineering, scaling, and encoding of the datasets.
"""

import logging
from typing import Dict, Any, Tuple
import pandas as pd

from ai_service.preprocessing.cleaning import (
    remove_duplicates,
    handle_missing_values,
    validate_timestamps,
    remove_invalid_records,
    handle_null_occupancy,
    handle_invalid_reservation_durations,
    handle_invalid_parking_sessions,
    remove_outliers,
)
from ai_service.preprocessing.validation import (
    validate_occupancy_schema,
    validate_reservation_schema,
    validate_session_schema,
)
from ai_service.features.feature_service import FeatureService
from ai_service.preprocessing.normalization import ScalerWrapper
from ai_service.preprocessing.encoding import CategoricalEncoder

logger = logging.getLogger(__name__)


class PreprocessingPipeline:
    """
    Orchestrates the entire cleaning, validation, feature engineering, normalization, and encoding flow.
    """

    def __init__(
        self,
        scaling_strategy: str = "standard",
        encoding_strategy: str = "onehot",
    ) -> None:
        self.scaling_strategy = scaling_strategy
        self.encoding_strategy = encoding_strategy
        
        # Initialize feature service
        self.feature_service = FeatureService()

        # Scalers for each training dataset
        self.occupancy_scaler = ScalerWrapper(strategy=scaling_strategy)
        self.reservation_scaler = ScalerWrapper(strategy=scaling_strategy)
        self.session_scaler = ScalerWrapper(strategy=scaling_strategy)
        self.forecast_scaler = ScalerWrapper(strategy=scaling_strategy)

        # Encoders for categorical features
        self.reservation_encoder = CategoricalEncoder(strategy=encoding_strategy)
        self.session_encoder = CategoricalEncoder(strategy=encoding_strategy)
        self.forecast_encoder = CategoricalEncoder(strategy=encoding_strategy)

    def clean_occupancy(self, df: pd.DataFrame) -> pd.DataFrame:
        """Runs the cleaning flow on occupancy data."""
        if len(df) == 0:
            return df
        
        # Remove duplicates
        df = remove_duplicates(df, subset=["facility_id", "zone_id", "collected_at"])
        # Validate timestamps
        df = validate_timestamps(df, timestamp_cols=["collected_at"])
        # Drop rows with null essential attributes
        df = remove_invalid_records(df, required_cols=["facility_id", "total_slots", "collected_at"])
        # Occupancy specific checks/recalculations
        df = handle_null_occupancy(df)
        # Outlier removal on occupancy metrics
        df = remove_outliers(df, columns=["occupied_slots", "occupancy_percentage"])
        
        return df

    def clean_reservation(self, df: pd.DataFrame) -> pd.DataFrame:
        """Runs the cleaning flow on reservation data."""
        if len(df) == 0:
            return df
            
        df = remove_duplicates(df, subset=["reservation_id"])
        df = validate_timestamps(df, timestamp_cols=["reservation_start", "reservation_end", "collected_at"])
        df = remove_invalid_records(df, required_cols=["reservation_id", "facility_id", "reservation_start", "reservation_end"])
        df = handle_invalid_reservation_durations(df)
        df = remove_outliers(df, columns=["duration_minutes"])
        
        return df

    def clean_session(self, df: pd.DataFrame) -> pd.DataFrame:
        """Runs the cleaning flow on session data."""
        if len(df) == 0:
            return df
            
        df = remove_duplicates(df, subset=["session_id"])
        df = validate_timestamps(df, timestamp_cols=["check_in_time", "check_out_time", "collected_at"])
        df = remove_invalid_records(df, required_cols=["session_id", "facility_id", "vehicle_type", "check_in_time"])
        df = handle_invalid_parking_sessions(df)
        # Outlier removal only for completed sessions duration/fee
        completed_sessions = df[df["check_out_time"].notna()]
        if len(completed_sessions) > 0:
            # We do it globally or fallback
            df = remove_outliers(df, columns=["duration_minutes", "parking_fee"])
            
        return df

    def run(
        self,
        raw_occupancy: pd.DataFrame,
        raw_reservation: pd.DataFrame,
        raw_session: pd.DataFrame,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        """
        Executes the full pipeline:
        Clean -> Validate -> Feature Generation -> Normalization -> Encoding.
        Returns:
          (occupancy_training, reservation_training, session_training, forecast_training, pipeline_metrics)
        """
        logger.info("Executing preprocessing pipeline...")
        metrics = {
            "raw_records": {
                "occupancy": len(raw_occupancy),
                "reservation": len(raw_reservation),
                "session": len(raw_session),
            },
            "validation_reports": {},
            "cleaned_records": {},
        }

        # 1. CLEANING
        clean_occ = self.clean_occupancy(raw_occupancy)
        clean_res = self.clean_reservation(raw_reservation)
        clean_sess = self.clean_session(raw_session)

        metrics["cleaned_records"] = {
            "occupancy": len(clean_occ),
            "reservation": len(clean_res),
            "session": len(clean_sess),
        }

        # 2. VALIDATION
        metrics["validation_reports"]["occupancy"] = validate_occupancy_schema(clean_occ)
        metrics["validation_reports"]["reservation"] = validate_reservation_schema(clean_res)
        metrics["validation_reports"]["session"] = validate_session_schema(clean_sess)

        # 3. FEATURE GENERATION
        # Generates lags, rolling window statistics, calendar indicators, and rates
        occ_features = self.feature_service.generate_all_occupancy_features(clean_occ)
        res_features = self.feature_service.generate_all_reservation_features(clean_res)
        sess_features = self.feature_service.generate_all_session_features(clean_sess)

        # Generate the consolidated time-series forecasting dataset
        forecast_features = self.feature_service.build_forecast_dataset(
            occupancy_df=clean_occ,
            reservation_df=clean_res,
            session_df=clean_sess,
        )

        # 4. NORMALIZATION & ENCODING
        # Process Occupancy Dataset
        if len(occ_features) > 0:
            # Scale numeric feature columns
            numeric_cols = [
                "occupancy_diff", "occupancy_growth_rate", "occupancy_trend"
            ] + [c for c in occ_features.columns if "lag_" in c or "roll_mean_" in c or "roll_max_" in c or "roll_min_" in c]
            numeric_cols = [c for c in numeric_cols if c in occ_features.columns]
            occ_features = self.occupancy_scaler.fit_transform(occ_features, numeric_cols)

        # Process Reservation Dataset
        if len(res_features) > 0:
            numeric_cols = ["duration_minutes", "lead_time_minutes"]
            numeric_cols = [c for c in numeric_cols if c in res_features.columns]
            res_features = self.reservation_scaler.fit_transform(res_features, numeric_cols)
            
            # Encode categorical status
            if "reservation_status" in res_features.columns:
                res_features = self.reservation_encoder.fit_transform(res_features, ["reservation_status"])

        # Process Session Dataset
        if len(sess_features) > 0:
            numeric_cols = ["duration_minutes", "parking_fee", "revenue_per_minute"]
            numeric_cols = [c for c in numeric_cols if c in sess_features.columns]
            sess_features = self.session_scaler.fit_transform(sess_features, numeric_cols)
            
            # Encode categorical vehicle type
            if "vehicle_type" in sess_features.columns:
                sess_features = self.session_encoder.fit_transform(sess_features, ["vehicle_type"])

        # Process Consolidated Forecast Dataset
        if len(forecast_features) > 0:
            # Scale numerical inputs
            numeric_cols = [
                "occupancy_percentage", "occupied_slots", "occupancy_diff",
                "occupancy_growth_rate", "occupancy_trend",
                "reservation_count", "reservations_in_prev_hour", "reservations_today",
                "reservation_density", "reservation_trend", "cancellation_rate",
                "average_reservation_duration", "reservation_growth",
                "entry_rate", "exit_rate", "sessions_per_hour", "sessions_per_day",
                "average_session_duration", "median_duration", "average_revenue_per_session",
                "parking_turnover", "session_density", "time_since_last_update"
            ] + [c for c in forecast_features.columns if "lag_" in c or "roll_" in c]
            numeric_cols = [c for c in numeric_cols if c in forecast_features.columns]
            forecast_features = self.forecast_scaler.fit_transform(forecast_features, numeric_cols)

            # Encode facility ID if desired
            if "facility_id" in forecast_features.columns:
                forecast_features = self.forecast_encoder.fit_transform(forecast_features, ["facility_id"])

        logger.info("Pipeline executed successfully.")
        return occ_features, res_features, sess_features, forecast_features, metrics
