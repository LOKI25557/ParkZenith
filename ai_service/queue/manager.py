"""
Virtual Queue Manager for ParkZenith AI Service.
Handles in-memory concurrency-safe queue state management.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ai_service.core.exceptions import MissingFacilityError, DatabaseError, DuplicateDataError
from ai_service.models.occupancy import OccupancyHistory

logger = logging.getLogger(__name__)


class VirtualQueueManager:
    """
    Manages active queues for facilities using in-memory storage and locks
    to guarantee concurrency safety during enqueue, dequeue, cancel, and position lookup.
    """

    def __init__(self) -> None:
        self._queues: Dict[str, List[str]] = {}  # facility_id -> list of user_id
        self._locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    async def _get_lock(self, facility_id: str) -> asyncio.Lock:
        """
        Retrieves or creates a Lock dedicated to a facility_id.
        """
        async with self._global_lock:
            if facility_id not in self._locks:
                self._locks[facility_id] = asyncio.Lock()
            return self._locks[facility_id]

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

    async def enqueue(self, db: AsyncSession, facility_id: str, user_id: str) -> int:
        """
        Enqueues a user in the facility virtual queue.
        Handles duplicates by returning their current position.
        """
        await self._validate_facility(db, facility_id)
        lock = await self._get_lock(facility_id)

        async with lock:
            q = self._queues.setdefault(facility_id, [])
            if user_id in q:
                logger.info("User %s already enqueued in facility %s.", user_id, facility_id)
                # Duplicate handling: return current position
                return q.index(user_id) + 1

            q.append(user_id)
            logger.info("Enqueued user %s to facility %s queue. Total queue size: %d", user_id, facility_id, len(q))
            return len(q)

    async def dequeue(self, db: AsyncSession, facility_id: str, user_id: Optional[str] = None) -> Optional[str]:
        """
        Pops the first user (if user_id is None) or removes a specific user from the queue.
        Handles empty queues and missing users gracefully.
        """
        await self._validate_facility(db, facility_id)
        lock = await self._get_lock(facility_id)

        async with lock:
            q = self._queues.get(facility_id, [])
            if not q:
                logger.info("Dequeue attempted on empty queue for facility %s.", facility_id)
                return None

            if user_id is None:
                popped_user = q.pop(0)
                logger.info("Dequeued front user %s from facility %s queue.", popped_user, facility_id)
                return popped_user

            if user_id in q:
                q.remove(user_id)
                logger.info("Dequeued specific user %s from facility %s queue.", user_id, facility_id)
                return user_id

            logger.info("User %s not found in facility %s queue for dequeue.", user_id, facility_id)
            return None

    async def cancel(self, db: AsyncSession, facility_id: str, user_id: str) -> bool:
        """
        Cancels a user's position in the queue.
        Returns True if cancelled, False if user was not in the queue.
        """
        await self._validate_facility(db, facility_id)
        lock = await self._get_lock(facility_id)

        async with lock:
            q = self._queues.get(facility_id, [])
            if user_id in q:
                q.remove(user_id)
                logger.info("Cancelled queue spot for user %s at facility %s.", user_id, facility_id)
                return True
            logger.info("Cancel request: user %s was not in facility %s queue.", user_id, facility_id)
            return False

    async def get_position(self, db: AsyncSession, facility_id: str, user_id: str) -> Optional[int]:
        """
        Looks up a user's current queue position (1-indexed).
        Returns None if user is not in the queue.
        """
        await self._validate_facility(db, facility_id)
        lock = await self._get_lock(facility_id)

        async with lock:
            q = self._queues.get(facility_id, [])
            if user_id in q:
                pos = q.index(user_id) + 1
                logger.info("Position lookup: user %s is at spot %d in facility %s.", user_id, pos, facility_id)
                return pos
            logger.info("Position lookup: user %s is not in facility %s queue.", user_id, facility_id)
            return None

    def clear_all(self) -> None:
        """
        Clears all virtual queues in memory (for testing purposes).
        """
        self._queues.clear()
        self._locks.clear()
