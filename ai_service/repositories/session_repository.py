"""
ParkingSessionRepository implementing async database operations for ParkingSessionHistory.
"""

from typing import List, Optional, Set
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, desc, and_

from ai_service.models.session import ParkingSessionHistory
from ai_service.repositories.base import BaseAsyncRepository
from ai_service.core.exceptions import DatabaseError


class ParkingSessionRepository(BaseAsyncRepository[ParkingSessionHistory]):
    """
    Repository handling data access logic for ParkingSessionHistory.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ParkingSessionHistory, session)

    async def get_existing_session_ids(
        self, session_ids: List[str]
    ) -> Set[str]:
        """
        Efficiently checks which session IDs already exist in the database.
        Used for deduplication during ingestion.
        """
        if not session_ids:
            return set()
        try:
            stmt = select(ParkingSessionHistory.session_id).where(
                ParkingSessionHistory.session_id.in_(session_ids)
            )
            result = await self.session.execute(stmt)
            return set(result.scalars().all())
        except Exception as exc:
            raise DatabaseError(
                message=f"Failed to check existing session IDs: {str(exc)}",
                details={"count": len(session_ids)},
            ) from exc

    async def get_latest(
        self, facility_id: Optional[str] = None, limit: int = 10
    ) -> List[ParkingSessionHistory]:
        """
        Retrieves the most recent parking session records ordered by collected_at descending.
        Optionally filters by facility_id.
        """
        try:
            stmt = select(ParkingSessionHistory).order_by(desc(ParkingSessionHistory.collected_at))
            if facility_id:
                stmt = stmt.where(ParkingSessionHistory.facility_id == facility_id)
            stmt = stmt.limit(limit)
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception as exc:
            raise DatabaseError(
                message=f"Failed to get latest parking session records: {str(exc)}",
                details={"facility_id": facility_id, "limit": limit},
            ) from exc

    async def get_between_dates(
        self,
        start_date: datetime,
        end_date: datetime,
        facility_id: Optional[str] = None,
    ) -> List[ParkingSessionHistory]:
        """
        Retrieves parking session history records with check_in_time between start_date and end_date.
        Optionally filters by facility_id.
        """
        try:
            filters = [
                ParkingSessionHistory.check_in_time >= start_date,
                ParkingSessionHistory.check_in_time <= end_date,
            ]
            if facility_id:
                filters.append(ParkingSessionHistory.facility_id == facility_id)

            stmt = (
                select(ParkingSessionHistory)
                .where(and_(*filters))
                .order_by(ParkingSessionHistory.check_in_time.asc())
            )
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception as exc:
            raise DatabaseError(
                message=f"Failed to fetch parking session records between dates: {str(exc)}",
                details={"start_date": str(start_date), "end_date": str(end_date)},
            ) from exc

    async def delete_old_records(self, before_date: datetime) -> int:
        """
        Deletes parking session history records collected prior to before_date.
        Returns the number of deleted records.
        """
        try:
            stmt = delete(ParkingSessionHistory).where(ParkingSessionHistory.collected_at < before_date)
            result = await self.session.execute(stmt)
            deleted_count = result.rowcount or 0
            return deleted_count
        except Exception as exc:
            raise DatabaseError(
                message=f"Failed to delete old parking session records: {str(exc)}",
                details={"before_date": str(before_date)},
            ) from exc
