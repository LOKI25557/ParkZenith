"""
OccupancyRepository implementing async database operations for OccupancyHistory.
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, desc, and_

from ai_service.models.occupancy import OccupancyHistory
from ai_service.repositories.base import BaseAsyncRepository
from ai_service.core.exceptions import DatabaseError


class OccupancyRepository(BaseAsyncRepository[OccupancyHistory]):
    """
    Repository handling data access logic for OccupancyHistory.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(OccupancyHistory, session)

    async def get_latest(
        self, facility_id: Optional[str] = None, limit: int = 10
    ) -> List[OccupancyHistory]:
        """
        Retrieves the most recent occupancy records ordered by collected_at descending.
        Optionally filters by facility_id.
        """
        try:
            stmt = select(OccupancyHistory).order_by(desc(OccupancyHistory.collected_at))
            if facility_id:
                stmt = stmt.where(OccupancyHistory.facility_id == facility_id)
            stmt = stmt.limit(limit)
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception as exc:
            raise DatabaseError(
                message=f"Failed to get latest occupancy records: {str(exc)}",
                details={"facility_id": facility_id, "limit": limit},
            ) from exc

    async def get_between_dates(
        self,
        start_date: datetime,
        end_date: datetime,
        facility_id: Optional[str] = None,
    ) -> List[OccupancyHistory]:
        """
        Retrieves occupancy history records between start_date and end_date.
        Optionally filters by facility_id.
        """
        try:
            filters = [
                OccupancyHistory.collected_at >= start_date,
                OccupancyHistory.collected_at <= end_date,
            ]
            if facility_id:
                filters.append(OccupancyHistory.facility_id == facility_id)

            stmt = (
                select(OccupancyHistory)
                .where(and_(*filters))
                .order_by(OccupancyHistory.collected_at.asc())
            )
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception as exc:
            raise DatabaseError(
                message=f"Failed to fetch occupancy records between dates: {str(exc)}",
                details={"start_date": str(start_date), "end_date": str(end_date)},
            ) from exc

    async def delete_old_records(self, before_date: datetime) -> int:
        """
        Deletes occupancy history records collected prior to before_date.
        Returns the number of deleted records.
        """
        try:
            stmt = delete(OccupancyHistory).where(OccupancyHistory.collected_at < before_date)
            result = await self.session.execute(stmt)
            deleted_count = result.rowcount or 0
            return deleted_count
        except Exception as exc:
            raise DatabaseError(
                message=f"Failed to delete old occupancy records: {str(exc)}",
                details={"before_date": str(before_date)},
            ) from exc
