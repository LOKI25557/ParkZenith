"""
Queue Service managing historical session query data, current occupancy details,
and coordinating with the QueueEngine.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import pandas as pd
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ai_service.core.exceptions import MissingFacilityError, DatabaseError
from ai_service.models.occupancy import OccupancyHistory
from ai_service.models.reservation import ReservationHistory
from ai_service.models.session import ParkingSessionHistory
from ai_service.queue.queue_engine import QueueEngine
from ai_service.queue.manager import VirtualQueueManager

logger = logging.getLogger(__name__)


class QueueService:
    """
    QueueService orchestrates database loading and invokes the QueueEngine.
    """

    def __init__(self, queue_engine: Optional[QueueEngine] = None) -> None:
        self.queue_engine = queue_engine or QueueEngine()
        self.virtual_queue_manager = VirtualQueueManager()

    async def enqueue_user(self, db: AsyncSession, facility_id: str, user_id: str) -> int:
        """
        Enqueues a user in the facility virtual queue.
        """
        return await self.virtual_queue_manager.enqueue(db, facility_id, user_id)

    async def dequeue_user(self, db: AsyncSession, facility_id: str, user_id: Optional[str] = None) -> Optional[str]:
        """
        Dequeues a user from the facility virtual queue.
        """
        return await self.virtual_queue_manager.dequeue(db, facility_id, user_id)

    async def cancel_user(self, db: AsyncSession, facility_id: str, user_id: str) -> bool:
        """
        Cancels a user's position in the queue.
        """
        return await self.virtual_queue_manager.cancel(db, facility_id, user_id)

    async def get_user_position(self, db: AsyncSession, facility_id: str, user_id: str) -> Optional[int]:
        """
        Looks up a user's current queue position.
        """
        return await self.virtual_queue_manager.get_position(db, facility_id, user_id)


    async def _validate_facility(self, db: AsyncSession, facility_id: str) -> None:
        """
        Validates if a facility exists. Raises MissingFacilityError if not found.
        """
        stmt = select(func.count()).select_from(OccupancyHistory).where(
            OccupancyHistory.facility_id == facility_id
        )
        try:
            count = (await db.execute(stmt)).scalar() or 0
        except Exception as exc:
            raise DatabaseError(
                message=f"Failed to validate facility ID: {str(exc)}"
            ) from exc

        if count == 0:
            raise MissingFacilityError(f"Facility '{facility_id}' has no historical records.")

    async def get_queue_prediction(
        self,
        db: AsyncSession,
        facility_id_raw: Any,
        eta_minutes: int = 0,
    ) -> Dict[str, Any]:
        """
        Predicts queue metrics for a specific facility at target horizon (ETA).
        """
        facility_id = str(facility_id_raw)
        
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
            raise MissingFacilityError(f"No occupancy logs found for facility_id: {facility_id}.")

        capacity = latest_occ.total_slots
        occupied_slots = latest_occ.occupied_slots

        # Ensure occupancy capacity/values are valid
        if capacity <= 0:
            # Handle capacity = 0 gracefully
            capacity = 100
            logger.warning("Facility total capacity is 0 or negative. Falling back to default capacity.")

        occupied_slots = max(0, min(occupied_slots, capacity))

        # 3. Query historical session count (30 days depth)
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
        try:
            sessions = (await db.execute(session_stmt)).scalars().all()
        except Exception as exc:
            raise DatabaseError(
                message=f"Failed to fetch session history: {str(exc)}"
            ) from exc

        session_data_count = len(sessions)
        avg_arrivals_per_hour = 0.0
        avg_departures_per_hour = 0.0
        
        # Calculate time-aware flow rates
        target_hour = now.hour
        target_dow = now.weekday()

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
            sess_df["check_in_dow"] = sess_df["check_in_time"].dt.dayofweek

            # Time-aware filter (hour & day of week)
            filtered_in = sess_df[
                (sess_df["check_in_hour"] == target_hour) &
                (sess_df["check_in_dow"] == target_dow)
            ]
            
            # Fallback to just target hour if no data for specific DOW
            if filtered_in.empty:
                filtered_in = sess_df[sess_df["check_in_hour"] == target_hour]

            unique_in_days = filtered_in["check_in_date"].nunique() or 1
            avg_arrivals_per_hour = len(filtered_in) / unique_in_days

            sess_checkout = sess_df.dropna(subset=["check_out_time"]).copy()
            if not sess_checkout.empty:
                sess_checkout["check_out_date"] = sess_checkout["check_out_time"].dt.date
                sess_checkout["check_out_hour"] = sess_checkout["check_out_time"].dt.hour
                sess_checkout["check_out_dow"] = sess_checkout["check_out_time"].dt.dayofweek

                filtered_out = sess_checkout[
                    (sess_checkout["check_out_hour"] == target_hour) &
                    (sess_checkout["check_out_dow"] == target_dow)
                ]
                if filtered_out.empty:
                    filtered_out = sess_checkout[sess_checkout["check_out_hour"] == target_hour]

                unique_out_days = filtered_out["check_out_date"].nunique() or 1
                avg_departures_per_hour = len(filtered_out) / unique_out_days

        # 4. Check upcoming reservations starting during prediction window [now, now + eta]
        eta_time = now + timedelta(minutes=eta_minutes)
        inc_stmt = select(func.count()).select_from(ReservationHistory).where(
            and_(
                ReservationHistory.facility_id == facility_id,
                ReservationHistory.reservation_start >= now,
                ReservationHistory.reservation_start <= eta_time,
                ReservationHistory.reservation_status.notin_(["CANCELLED", "NO_SHOW"])
            )
        )
        try:
            reservations_count = (await db.execute(inc_stmt)).scalar() or 0
        except Exception as exc:
            raise DatabaseError(
                message=f"Failed to query database for reservations: {str(exc)}"
            ) from exc

        has_reservations = reservations_count > 0

        # Get actual queue length from virtual queue manager in-memory state
        actual_queue_length = 0
        if self.virtual_queue_manager and hasattr(self.virtual_queue_manager, "_queues"):
            actual_queue_length = len(self.virtual_queue_manager._queues.get(facility_id, []))

        # 5. Process everything through the QueueEngine
        result = self.queue_engine.process(
            facility_id=facility_id,
            capacity=capacity,
            occupied_slots=occupied_slots,
            arrival_rate_per_hour=avg_arrivals_per_hour,
            departure_rate_per_hour=avg_departures_per_hour,
            eta_minutes=eta_minutes,
            session_data_count=session_data_count,
            has_reservations=has_reservations,
            actual_queue_length=actual_queue_length,
        )

        return result
