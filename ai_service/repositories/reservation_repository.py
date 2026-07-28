"""
ReservationRepository implementing async database operations for ReservationHistory.
"""

from typing import List, Optional, Set
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, desc, and_

from ai_service.models.reservation import ReservationHistory
from ai_service.repositories.base import BaseAsyncRepository
from ai_service.core.exceptions import DatabaseError


class ReservationRepository(BaseAsyncRepository[ReservationHistory]):
    """
    Repository handling data access logic for ReservationHistory.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ReservationHistory, session)

    async def get_existing_reservation_ids(
        self, reservation_ids: List[str]
    ) -> Set[str]:
        """
        Efficiently checks which reservation IDs already exist in the database.
        Used for deduplication during ingestion.
        """
        if not reservation_ids:
            return set()
        try:
            stmt = select(ReservationHistory.reservation_id).where(
                ReservationHistory.reservation_id.in_(reservation_ids)
            )
            result = await self.session.execute(stmt)
            return set(result.scalars().all())
        except Exception as exc:
            raise DatabaseError(
                message=f"Failed to check existing reservation IDs: {str(exc)}",
                details={"count": len(reservation_ids)},
            ) from exc

    async def get_latest(
        self, facility_id: Optional[str] = None, limit: int = 10
    ) -> List[ReservationHistory]:
        """
        Retrieves the most recent reservation records ordered by collected_at descending.
        Optionally filters by facility_id.
        """
        try:
            stmt = select(ReservationHistory).order_by(desc(ReservationHistory.collected_at))
            if facility_id:
                stmt = stmt.where(ReservationHistory.facility_id == facility_id)
            stmt = stmt.limit(limit)
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception as exc:
            raise DatabaseError(
                message=f"Failed to get latest reservation records: {str(exc)}",
                details={"facility_id": facility_id, "limit": limit},
            ) from exc

    async def get_between_dates(
        self,
        start_date: datetime,
        end_date: datetime,
        facility_id: Optional[str] = None,
    ) -> List[ReservationHistory]:
        """
        Retrieves reservation history records starting between start_date and end_date.
        Optionally filters by facility_id.
        """
        try:
            filters = [
                ReservationHistory.reservation_start >= start_date,
                ReservationHistory.reservation_start <= end_date,
            ]
            if facility_id:
                filters.append(ReservationHistory.facility_id == facility_id)

            stmt = (
                select(ReservationHistory)
                .where(and_(*filters))
                .order_by(ReservationHistory.reservation_start.asc())
            )
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception as exc:
            raise DatabaseError(
                message=f"Failed to fetch reservation records between dates: {str(exc)}",
                details={"start_date": str(start_date), "end_date": str(end_date)},
            ) from exc

    async def delete_old_records(self, before_date: datetime) -> int:
        """
        Deletes reservation history records collected prior to before_date.
        Returns the number of deleted records.
        """
        try:
            stmt = delete(ReservationHistory).where(ReservationHistory.collected_at < before_date)
            result = await self.session.execute(stmt)
            deleted_count = result.rowcount or 0
            return deleted_count
        except Exception as exc:
            raise DatabaseError(
                message=f"Failed to delete old reservation records: {str(exc)}",
                details={"before_date": str(before_date)},
            ) from exc
