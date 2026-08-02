"""
Forecasting Service managing predictions, model training, and metrics queries.
"""

import logging
from typing import Dict, Any, Optional
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from ..core.exceptions import ModelUnavailableError, InsufficientDataError, MissingFacilityError
from ..ml.forecasting import OccupancyForecaster
from ..models.occupancy import OccupancyHistory
from ..models.reservation import ReservationHistory
from ..models.session import ParkingSessionHistory
from ..preprocessing.pipeline import PreprocessingPipeline

logger = logging.getLogger(__name__)


class ForecastingService:
    """
    Forecasting Service orchestrating ML module calls and raw data retrieval.
    """

    def __init__(self, forecaster: Optional[OccupancyForecaster] = None) -> None:
        self.forecaster = forecaster or OccupancyForecaster()
        # Eagerly attempt to load the model package if available
        self.forecaster.load()

    def get_status(self) -> Dict[str, Any]:
        """
        Returns status indicating if the forecasting models are ready.
        """
        is_ready = self.forecaster.is_loaded
        return {
            "status": "READY" if is_ready else "NOT_TRAINED",
            "models_loaded": is_ready,
            "trained_horizons": list(self.forecaster.get_best_model_names().keys()) if is_ready else []
        }

    def get_metrics(self) -> Dict[str, Any]:
        """
        Returns metrics for the trained forecasting models.
        """
        if not self.forecaster.is_loaded:
            raise ModelUnavailableError("Forecasting models have not been trained or loaded yet.")
        return {
            "best_models": self.forecaster.get_best_model_names(),
            "metrics": self.forecaster.get_metrics()
        }

    async def train_models(self, db: AsyncSession, export_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Triggers full training pipeline for default horizons.
        """
        logger.info("Forecasting model training request received.")
        try:
            summary = await self.forecaster.train_all(db, export_path)
            return {
                "message": "Model training completed successfully.",
                "horizons": summary
            }
        except Exception as e:
            logger.exception("Error occurred during model training: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Model training failed: {str(e)}"
            )

    async def _fetch_and_prepare_latest_features(
        self,
        db: AsyncSession,
        facility_id: int
    ) -> tuple[pd.DataFrame, float]:
        """
        Retrieves recent historical records from database for a facility,
        runs them through the cleaning and feature engineering pipelines,
        and returns the latest feature vector along with the raw current occupancy.
        """
        logger.info("Fetching database logs for facility_id: %d", facility_id)

        # Query raw history from tables
        occ_stmt = select(OccupancyHistory).where(OccupancyHistory.facility_id == facility_id)
        res_stmt = select(ReservationHistory).where(ReservationHistory.facility_id == facility_id)
        sess_stmt = select(ParkingSessionHistory).where(ParkingSessionHistory.facility_id == facility_id)

        occ_res = await db.execute(occ_stmt)
        res_res = await db.execute(res_stmt)
        sess_res = await db.execute(sess_stmt)

        occ_records = occ_res.scalars().all()
        res_records = res_res.scalars().all()
        sess_records = sess_res.scalars().all()

        if not occ_records:
            raise MissingFacilityError(f"No occupancy logs found for facility_id: {facility_id}. Cannot compile features.")

        # Map to dataframes
        occ_data = [
            {
                "id": r.id,
                "facility_id": r.facility_id,
                "zone_id": r.zone_id,
                "total_slots": r.total_slots,
                "occupied_slots": r.occupied_slots,
                "available_slots": r.available_slots,
                "occupancy_percentage": r.occupancy_percentage,
                "collected_at": r.collected_at,
            }
            for r in occ_records
        ]
        occ_df = pd.DataFrame(occ_data)
        occ_df["collected_at"] = pd.to_datetime(occ_df["collected_at"], utc=True)
        occ_df = occ_df.sort_values(by="collected_at")
        
        # Get raw current occupancy
        current_occupancy = float(occ_df.iloc[-1]["occupancy_percentage"])

        res_data = [
            {
                "id": r.id,
                "reservation_id": r.reservation_id,
                "facility_id": r.facility_id,
                "slot_id": r.slot_id,
                "reservation_status": r.reservation_status,
                "reservation_start": r.reservation_start,
                "reservation_end": r.reservation_end,
                "duration_minutes": r.duration_minutes,
                "collected_at": r.collected_at,
            }
            for r in res_records
        ]
        res_df = pd.DataFrame(res_data)
        if len(res_df) > 0:
            for col in ["reservation_start", "reservation_end", "collected_at"]:
                res_df[col] = pd.to_datetime(res_df[col], utc=True)

        sess_data = [
            {
                "id": r.id,
                "session_id": r.session_id,
                "facility_id": r.facility_id,
                "vehicle_type": r.vehicle_type,
                "check_in_time": r.check_in_time,
                "check_out_time": r.check_out_time,
                "duration_minutes": r.duration_minutes,
                "parking_fee": r.parking_fee,
                "collected_at": r.collected_at,
            }
            for r in sess_records
        ]
        sess_df = pd.DataFrame(sess_data)
        if len(sess_df) > 0:
            for col in ["check_in_time", "check_out_time", "collected_at"]:
                sess_df[col] = pd.to_datetime(sess_df[col], utc=True)

        # Run preprocessing pipeline (which encodes/normalizes features identically to training)
        pipeline = PreprocessingPipeline()
        _, _, _, forecast_features, _ = pipeline.run(
            raw_occupancy=occ_df,
            raw_reservation=res_df,
            raw_session=sess_df,
            resample_freq="15min"
        )

        if len(forecast_features) == 0:
            raise InsufficientDataError("Failed to generate consolidated forecasting features. Too few data points.")

        # Take the most recent feature vector
        latest_features_df = forecast_features.tail(1)
        return latest_features_df, current_occupancy

    async def get_forecast_snapshot(
        self,
        db: AsyncSession,
        facility_id: int,
        primary_horizon_minutes: int
    ) -> Dict[str, Any]:
        """
        Generates forecast predictions for 15, 30, and 60 minutes intervals,
        returning the snapshot payload with confidence.
        """
        if not self.forecaster.is_loaded:
            # Try to load, if not trained raise error
            if not self.forecaster.load():
                raise ModelUnavailableError("Forecasting models are not trained. Please train the model first.")

        features_df, current_occ = await self._fetch_and_prepare_latest_features(db, facility_id)

        # Generate predictions
        try:
            pred_15 = self.forecaster.predict(15, features_df)
            pred_30 = self.forecaster.predict(30, features_df)
            pred_60 = self.forecaster.predict(60, features_df)
        except Exception as e:
            logger.exception("Prediction run failed: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Forecasting prediction failed: {str(e)}"
            )

        # Determine confidence of the queried primary horizon
        metrics = self.forecaster.get_metrics()
        h_str = str(primary_horizon_minutes)
        confidence = metrics.get(h_str, {}).get("confidence", 95.0)

        return {
            "facility_id": facility_id,
            "current_occupancy": current_occ,
            "prediction_15": pred_15,
            "prediction_30": pred_30,
            "prediction_60": pred_60,
            "confidence": round(confidence, 2)
        }

    async def get_custom_forecast(
        self,
        db: AsyncSession,
        facility_id: int,
        target_minutes: int,
        export_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates prediction for a custom interval.
        Dynamically trains the target regressor if missing.
        """
        if target_minutes <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target prediction minutes must be positive."
            )

        # Ensure model is ready (and trains dynamically if missing)
        logger.info("Custom forecast request for %d minutes...", target_minutes)
        meta = await self.forecaster.get_or_train_custom_horizon(db, target_minutes, export_path)
        
        features_df, current_occ = await self._fetch_and_prepare_latest_features(db, facility_id)
        
        try:
            pred = self.forecaster.predict(target_minutes, features_df)
        except Exception as e:
            logger.exception("Prediction run for custom horizon failed: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Forecasting prediction failed: {str(e)}"
            )

        confidence = meta["metrics"]["confidence"]

        return {
            "facility_id": facility_id,
            "current_occupancy": current_occ,
            "prediction_custom": pred,
            "confidence": round(confidence, 2)
        }


forecasting_service = ForecastingService()
