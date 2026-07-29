"""
Feature Service module for ParkZenith Feature Engineering.
Coordinates occupancy, reservation, and session feature generation, and aggregates them into a consolidated forecast training dataset.
"""

import logging
import pandas as pd

from ai_service.features.time_features import generate_time_features
from ai_service.features.occupancy_features import generate_occupancy_features
from ai_service.features.reservation_features import (
    generate_reservation_transaction_features,
    aggregate_reservation_features_hourly,
)
from ai_service.features.session_features import (
    generate_session_transaction_features,
    aggregate_session_features_hourly,
)

logger = logging.getLogger(__name__)


class FeatureService:
    """
    Coordinates building specific features and assembling the consolidated forecasting dataset.
    """

    def generate_all_occupancy_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Cleans and generates features for occupancy history data.
        """
        if len(df) == 0:
            return df
        
        # 1. Base time features
        df_feats = generate_time_features(df, timestamp_col="collected_at", group_cols=["facility_id"])
        # 2. Occupancy lag and rolling features
        df_feats = generate_occupancy_features(df_feats, timestamp_col="collected_at")
        
        return df_feats

    def generate_all_reservation_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generates transaction-level features for reservation history.
        """
        if len(df) == 0:
            return df
            
        # 1. Base transaction features
        df_feats = generate_reservation_transaction_features(df)
        # 2. Time features
        df_feats = generate_time_features(df_feats, timestamp_col="reservation_start")
        
        return df_feats

    def generate_all_session_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generates transaction-level features for parking session history.
        """
        if len(df) == 0:
            return df
            
        # 1. Base transaction features
        df_feats = generate_session_transaction_features(df)
        # 2. Time features
        df_feats = generate_time_features(df_feats, timestamp_col="check_in_time")
        
        return df_feats

    def build_forecast_dataset(
        self,
        occupancy_df: pd.DataFrame,
        reservation_df: pd.DataFrame,
        session_df: pd.DataFrame,
        resample_freq: str = "h",
    ) -> pd.DataFrame:
        """
        Builds a consolidated forecasting dataset by resampling and merging occupancy,
        reservation, and session features at a regular frequency (default hourly).
        """
        logger.info("Building consolidated forecasting dataset...")
        
        if len(occupancy_df) == 0:
            logger.warning("Occupancy dataset is empty. Cannot build consolidated forecast dataset.")
            return pd.DataFrame()

        # 1. Resample occupancy to regular intervals (default hourly) per facility/zone
        occ_df = occupancy_df.copy()
        occ_df["timestamp"] = pd.to_datetime(occ_df["collected_at"], utc=True).dt.floor(resample_freq)
        
        # Determine grouping columns (handle nullable zone_id)
        if "zone_id" in occ_df.columns:
            occ_df["_zone_filled"] = occ_df["zone_id"].fillna("ALL_ZONES")
            occ_group_cols = ["facility_id", "_zone_filled", "timestamp"]
        else:
            occ_group_cols = ["facility_id", "timestamp"]

        # Average metrics within the hourly bin
        occ_hourly = occ_df.groupby(occ_group_cols).agg(
            total_slots=("total_slots", "last"),
            occupied_slots=("occupied_slots", "mean"),
            occupancy_percentage=("occupancy_percentage", "mean"),
        ).reset_index()

        # Re-apply occupancy features (rolling stats, lags) on the resampled hourly grid
        occ_hourly = generate_occupancy_features(
            occ_hourly,
            percentage_col="occupancy_percentage",
            occupied_col="occupied_slots",
            total_col="total_slots",
            timestamp_col="timestamp",
        )

        # 2. Aggregate reservations hourly
        res_hourly = pd.DataFrame()
        if len(reservation_df) > 0:
            # We assume total capacity is matched, or fallback to default
            res_hourly = aggregate_reservation_features_hourly(reservation_df, start_col="reservation_start")

        # 3. Aggregate sessions hourly
        sess_hourly = pd.DataFrame()
        if len(session_df) > 0:
            sess_hourly = aggregate_session_features_hourly(session_df, check_in_col="check_in_time")

        # 4. Merge all together
        # Left merge occupancy (our base timeline) with reservation and session metrics
        merged_df = occ_hourly.copy()
        
        # Merge Reservations
        if not res_hourly.empty:
            merged_df = pd.merge(
                merged_df,
                res_hourly,
                on=["facility_id", "timestamp"],
                how="left"
            )
            # Fill missing reservation counts/metrics with 0
            res_cols = [c for c in res_hourly.columns if c not in ["facility_id", "timestamp"]]
            merged_df[res_cols] = merged_df[res_cols].fillna(0.0)

        # Merge Sessions
        if not sess_hourly.empty:
            merged_df = pd.merge(
                merged_df,
                sess_hourly,
                on=["facility_id", "timestamp"],
                how="left"
            )
            # Fill missing session counts/metrics with 0
            sess_cols = [c for c in sess_hourly.columns if c not in ["facility_id", "timestamp"]]
            merged_df[sess_cols] = merged_df[sess_cols].fillna(0.0)

        # 5. Generate time features on the merged hourly timeline
        group_cols = ["facility_id"]
        if "_zone_filled" in merged_df.columns:
            group_cols.append("_zone_filled")
        
        merged_df = generate_time_features(
            merged_df,
            timestamp_col="timestamp",
            prefix="time_",
            group_cols=group_cols
        )

        # Clean up temporary columns
        if "_zone_filled" in merged_df.columns:
            merged_df = merged_df.drop(columns=["_zone_filled"])

        logger.info("Consolidated forecast dataset built successfully. Row count: %d", len(merged_df))
        return merged_df
