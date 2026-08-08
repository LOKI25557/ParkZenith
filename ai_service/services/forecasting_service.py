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
        occ_stmt = (
            select(OccupancyHistory)
            .where(OccupancyHistory.facility_id == facility_id)
            .order_by(OccupancyHistory.collected_at.desc())
            .limit(100)
        )
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
        # Establish a safe baseline for current occupancy in case of failure
        current_occ = 0.0
        try:
            occ_stmt = (
                select(OccupancyHistory)
                .where(OccupancyHistory.facility_id == facility_id)
                .order_by(OccupancyHistory.collected_at.desc())
                .limit(1)
            )
            latest_occ = (await db.execute(occ_stmt)).scalar_one_or_none()
            if latest_occ:
                current_occ = float(latest_occ.occupancy_percentage)
        except Exception:
            pass

        fallback_payload = {
            "facility_id": facility_id,
            "current_occupancy": current_occ,
            "prediction_15": current_occ,
            "prediction_30": current_occ,
            "prediction_60": current_occ,
            "confidence": 0.0,
            "prediction_status": "UNAVAILABLE"
        }

        # Validate model package availability
        if not self.forecaster.is_loaded:
            if not self.forecaster.load():
                logger.warning("Forecasting models are not trained or loaded. Returning fallback.")
                return fallback_payload

        # Validate prediction horizon
        if primary_horizon_minutes not in (15, 30, 60):
            logger.warning("Unsupported forecast snapshot horizon: %d. Returning fallback.", primary_horizon_minutes)
            return fallback_payload

        # Handle features extraction safely
        try:
            features_df, current_occ = await self._fetch_and_prepare_latest_features(db, facility_id)
        except Exception as e:
            logger.warning("Failed to prepare latest features for facility %d: %s. Returning fallback.", facility_id, str(e))
            return fallback_payload

        # Generate predictions safely
        import math
        try:
            pred_15 = self.forecaster.predict(15, features_df)
            pred_30 = self.forecaster.predict(30, features_df)
            pred_60 = self.forecaster.predict(60, features_df)
            
            # Prevent NaN/inf values
            if not (math.isfinite(pred_15) and math.isfinite(pred_30) and math.isfinite(pred_60)):
                raise ValueError("Forecast returned NaN or non-finite values.")
        except Exception as e:
            logger.warning("Prediction execution failed for facility %d: %s. Returning fallback.", facility_id, str(e))
            return fallback_payload

        # Determine confidence of the queried primary horizon
        metrics = self.forecaster.get_metrics()
        h_str = str(primary_horizon_minutes)
        confidence = metrics.get(h_str, {}).get("confidence", 95.0)

        # Apply event adjustments
        try:
            from datetime import datetime, timezone, timedelta
            from ai_service.services.event_service import EventIntelligenceService
            event_service = EventIntelligenceService()
            fid_str = str(facility_id)
            now_utc = datetime.now(timezone.utc)

            comp_15 = await event_service.get_composite_impact(db, fid_str, now_utc + timedelta(minutes=15))
            pred_15 = min(100.0, max(0.0, pred_15 + comp_15.get("composite_extra_occupancy_percentage", 0.0)))

            comp_30 = await event_service.get_composite_impact(db, fid_str, now_utc + timedelta(minutes=30))
            pred_30 = min(100.0, max(0.0, pred_30 + comp_30.get("composite_extra_occupancy_percentage", 0.0)))

            comp_60 = await event_service.get_composite_impact(db, fid_str, now_utc + timedelta(minutes=60))
            pred_60 = min(100.0, max(0.0, pred_60 + comp_60.get("composite_extra_occupancy_percentage", 0.0)))
        except Exception as e:
            logger.warning("Failed to apply event adjustments to forecast snapshot: %s", str(e))

        return {
            "facility_id": facility_id,
            "current_occupancy": current_occ,
            "prediction_15": round(pred_15, 2),
            "prediction_30": round(pred_30, 2),
            "prediction_60": round(pred_60, 2),
            "confidence": round(confidence, 2),
            "prediction_status": "SUCCESS"
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
        # Establish baseline fallback current occupancy
        current_occ = 0.0
        try:
            occ_stmt = (
                select(OccupancyHistory)
                .where(OccupancyHistory.facility_id == facility_id)
                .order_by(OccupancyHistory.collected_at.desc())
                .limit(1)
            )
            latest_occ = (await db.execute(occ_stmt)).scalar_one_or_none()
            if latest_occ:
                current_occ = float(latest_occ.occupancy_percentage)
        except Exception:
            pass

        fallback_payload = {
            "facility_id": facility_id,
            "current_occupancy": current_occ,
            "prediction_custom": current_occ,
            "confidence": 0.0,
            "prediction_status": "UNAVAILABLE"
        }

        if target_minutes <= 0:
            logger.warning("Custom forecast requested with invalid horizon: %d. Returning fallback.", target_minutes)
            return fallback_payload

        # Ensure model is ready (and trains dynamically if missing)
        try:
            logger.info("Custom forecast request for %d minutes...", target_minutes)
            meta = await self.forecaster.get_or_train_custom_horizon(db, target_minutes, export_path)
        except Exception as e:
            logger.warning("Custom horizon model training/loading failed for %d minutes: %s. Returning fallback.", target_minutes, str(e))
            return fallback_payload
        
        # Load features safely
        try:
            features_df, current_occ = await self._fetch_and_prepare_latest_features(db, facility_id)
        except Exception as e:
            logger.warning("Failed to prepare features for custom forecast of facility %d: %s. Returning fallback.", facility_id, str(e))
            return fallback_payload
        
        # Run inference safely
        try:
            pred = self.forecaster.predict(target_minutes, features_df)
            import math
            if not math.isfinite(pred):
                raise ValueError("Custom forecast returned NaN or non-finite values.")
        except Exception as e:
            logger.warning("Prediction inference failed for custom horizon %d: %s. Returning fallback.", target_minutes, str(e))
            return fallback_payload

        confidence = meta.get("metrics", {}).get("confidence", 95.0)

        # Apply event adjustments
        try:
            from datetime import datetime, timezone, timedelta
            from ai_service.services.event_service import EventIntelligenceService
            event_service = EventIntelligenceService()
            fid_str = str(facility_id)
            now_utc = datetime.now(timezone.utc)

            comp_custom = await event_service.get_composite_impact(db, fid_str, now_utc + timedelta(minutes=target_minutes))
            pred = min(100.0, max(0.0, pred + comp_custom.get("composite_extra_occupancy_percentage", 0.0)))
        except Exception as e:
            logger.warning("Failed to apply event adjustments to custom forecast: %s", str(e))

        return {
            "facility_id": facility_id,
            "current_occupancy": current_occ,
            "prediction_custom": round(pred, 2),
            "confidence": round(confidence, 2),
            "prediction_status": "SUCCESS"
        }


forecasting_service = ForecastingService()
