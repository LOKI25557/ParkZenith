"""
AvailabilityService managing arrival availability predictions, expected slots, and summary statistics.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ai_service.core.exceptions import MissingFacilityError, DatabaseError
from ai_service.models.occupancy import OccupancyHistory
from ai_service.models.reservation import ReservationHistory
from ai_service.models.session import ParkingSessionHistory
from ai_service.availability.availability_engine import AvailabilityEngine
from ai_service.services.forecasting_service import ForecastingService

logger = logging.getLogger(__name__)


class AvailabilityService:
    """
    Availability Service orchestrating data loading and invoking the AvailabilityEngine.
    """

    def __init__(self, forecasting_service: Optional[ForecastingService] = None) -> None:
        self.forecasting_service = forecasting_service or ForecastingService()

    async def _validate_facility(self, db: AsyncSession, facility_id: str) -> None:
        """
        Validates if a facility exists by checking if there are occupancy records.
        Raises MissingFacilityError if the facility does not exist.
        """
        stmt = select(func.count()).select_from(OccupancyHistory).where(
            OccupancyHistory.facility_id == facility_id
        )
        count = (await db.execute(stmt)).scalar() or 0
        if count == 0:
            raise MissingFacilityError(f"Facility '{facility_id}' has no historical records.")

    async def get_status(self) -> Dict[str, Any]:
        """
        Returns the status of the availability service.
        """
        forecast_status = self.forecasting_service.get_status()
        is_ready = forecast_status.get("status") == "READY"
        
        return {
            "status": "READY" if is_ready else "DEGRADED",
            "forecasting_service_ready": is_ready,
            "message": (
                "Availability Prediction Service is fully functional with ML Forecasting support."
                if is_ready else
                "Availability Prediction Service is running in degraded mode (Flow fallback only)."
            )
        }

    async def predict_facility_availability(
        self,
        db: AsyncSession,
        facility_id_raw: Any,
        eta_minutes: int
    ) -> Dict[str, Any]:
        """
        Calculates occupancy and availability probability at arrival (ETA).
        """
        if eta_minutes < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ETA minutes must be greater than or equal to 0."
            )

        facility_id = str(facility_id_raw)
        logger.info("Starting availability prediction for facility: %s, ETA: %d mins", facility_id, eta_minutes)

        # 1. Validate facility
        await self._validate_facility(db, facility_id)

        # 2. Get latest occupancy record
        occ_stmt = (
            select(OccupancyHistory)
            .where(OccupancyHistory.facility_id == facility_id)
            .order_by(OccupancyHistory.collected_at.desc())
            .limit(1)
        )
        try:
            latest_occ = (await db.execute(occ_stmt)).scalar_one_or_none()
        except Exception as exc:
            raise DatabaseError(
                message=f"Failed to query database for facility occupancy: {str(exc)}"
            ) from exc

        if not latest_occ:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No occupancy logs found for facility_id: {facility_id}."
            )

        capacity = latest_occ.total_slots
        current_occupied = latest_occ.occupied_slots

        # Ensure occupancy values are valid
        if capacity <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Facility capacity must be greater than zero."
            )
        if current_occupied < 0 or current_occupied > capacity:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid occupied slots value: {current_occupied} for capacity {capacity}."
            )

        # 3. Query historical count (data depth)
        hist_stmt = select(func.count()).select_from(OccupancyHistory).where(
            OccupancyHistory.facility_id == facility_id
        )
        hist_count = (await db.execute(hist_stmt)).scalar() or 0

        # 4. Fetch session history (last 30 days) to compute flow rates
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        session_stmt = (
            select(ParkingSessionHistory)
            .where(
                and_(
                    ParkingSessionHistory.facility_id == facility_id,
                    ParkingSessionHistory.check_in_time >= thirty_days_ago
                )
            )
        )
        sessions = (await db.execute(session_stmt)).scalars().all()

        # Calculate arrival and departure rates for the current hour
        target_hour = now.hour
        avg_arrivals_per_hour = 0.0
        avg_departures_per_hour = 0.0

        if sessions:
            sess_data = [
                {
                    "check_in_time": s.check_in_time,
                    "check_out_time": s.check_out_time
                }
                for s in sessions
            ]
            sess_df = pd.DataFrame(sess_data)
            sess_df["check_in_time"] = pd.to_datetime(sess_df["check_in_time"], utc=True)
            sess_df["check_out_time"] = pd.to_datetime(sess_df["check_out_time"], utc=True)

            sess_df["check_in_date"] = sess_df["check_in_time"].dt.date
            sess_df["check_in_hour"] = sess_df["check_in_time"].dt.hour

            check_ins_target = sess_df[sess_df["check_in_hour"] == target_hour]
            unique_in_days = sess_df["check_in_date"].nunique() or 1
            avg_arrivals_per_hour = len(check_ins_target) / unique_in_days

            sess_checkout = sess_df.dropna(subset=["check_out_time"]).copy()
            if not sess_checkout.empty:
                sess_checkout["check_out_date"] = sess_checkout["check_out_time"].dt.date
                sess_checkout["check_out_hour"] = sess_checkout["check_out_time"].dt.hour
                
                check_outs_target = sess_checkout[sess_checkout["check_out_hour"] == target_hour]
                unique_out_days = sess_checkout["check_out_date"].nunique() or 1
                avg_departures_per_hour = len(check_outs_target) / unique_out_days

        # 5. Query upcoming reservations starting/ending during [now, now + eta]
        eta_time = now + timedelta(minutes=eta_minutes)
        
        inc_stmt = select(func.count()).select_from(ReservationHistory).where(
            and_(
                ReservationHistory.facility_id == facility_id,
                ReservationHistory.reservation_start >= now,
                ReservationHistory.reservation_start <= eta_time,
                ReservationHistory.reservation_status.notin_(["CANCELLED", "NO_SHOW"])
            )
        )
        out_stmt = select(func.count()).select_from(ReservationHistory).where(
            and_(
                ReservationHistory.facility_id == facility_id,
                ReservationHistory.reservation_end >= now,
                ReservationHistory.reservation_end <= eta_time,
                ReservationHistory.reservation_status.notin_(["CANCELLED", "NO_SHOW"])
            )
        )

        incoming_reservations = (await db.execute(inc_stmt)).scalar() or 0
        outgoing_reservations = (await db.execute(out_stmt)).scalar() or 0

        # 6. Load forecasting predictions if eta > 0
        forecast_occupancy_pct = None
        forecasting_confidence = None

        if eta_minutes > 0:
            try:
                forecast_res = await self.forecasting_service.get_custom_forecast(
                    db=db,
                    facility_id=int(facility_id) if facility_id.isdigit() else facility_id,
                    target_minutes=eta_minutes
                )
                forecast_occupancy_pct = forecast_res.get("prediction_custom")
                forecasting_confidence = forecast_res.get("confidence")
                logger.info("Forecast successfully loaded for facility %s at ETA %d", facility_id, eta_minutes)
            except Exception as e:
                logger.warning(
                    "ML forecasting unavailable for facility %s at ETA %d: %s. Falling back to flow-based.",
                    facility_id, eta_minutes, str(e)
                )

        # 7. Run predictor calculations
        prediction = AvailabilityEngine.predict_availability(
            facility_id=facility_id_raw,
            capacity=capacity,
            current_occupied=current_occupied,
            avg_arrivals_per_hour=avg_arrivals_per_hour,
            avg_departures_per_hour=avg_departures_per_hour,
            incoming_reservations=incoming_reservations,
            outgoing_reservations=outgoing_reservations,
            forecast_occupancy_pct=forecast_occupancy_pct,
            forecasting_confidence=forecasting_confidence,
            historical_records_count=hist_count,
            eta_minutes=eta_minutes
        )

        logger.info("Availability calculated for facility_id: %s", facility_id)
        return prediction

    async def get_availability_summary(
        self,
        db: AsyncSession,
        eta_minutes: int = 20
    ) -> Dict[str, Any]:
        """
        Generates summarized availability prediction statistics across all active facilities.
        """
        # Query distinct facilities in occupancy history
        facility_stmt = select(OccupancyHistory.facility_id).distinct()
        facility_ids = (await db.execute(facility_stmt)).scalars().all()
        
        predictions: List[Dict[str, Any]] = []
        high_risk_count = 0
        medium_risk_count = 0
        low_risk_count = 0
        total_prob = 0.0
        total_conf = 0.0

        for f_id in facility_ids:
            try:
                pred = await self.predict_facility_availability(db, f_id, eta_minutes)
                predictions.append(pred)
                
                risk = pred["occupancy_risk"]
                if risk == "HIGH":
                    high_risk_count += 1
                elif risk == "MEDIUM":
                    medium_risk_count += 1
                else:
                    low_risk_count += 1
                
                total_prob += pred["availability_probability"]
                total_conf += pred["confidence"]
            except Exception as e:
                logger.error("Failed to predict availability for facility %s in summary: %s", str(f_id), str(e))

        total_predicted = len(predictions)
        avg_prob = round(total_prob / total_predicted, 2) if total_predicted > 0 else 0.0
        avg_conf = round(total_conf / total_predicted, 2) if total_predicted > 0 else 0.0

        return {
            "total_facilities_predicted": total_predicted,
            "average_probability": avg_prob,
            "average_confidence": avg_conf,
            "high_risk_count": high_risk_count,
            "medium_risk_count": medium_risk_count,
            "low_risk_count": low_risk_count,
            "predictions": predictions
        }
