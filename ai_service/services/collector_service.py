"""
CollectorService module for orchestrating collection tasks and status queries.
Adheres to clean architecture by working via repositories and collectors.
"""

import logging
from typing import Dict
from sqlalchemy.ext.asyncio import AsyncSession

from ai_service.utils.backend_client import BackendAPIClient
from ai_service.collectors.occupancy_collector import OccupancyCollector
from ai_service.collectors.reservation_collector import ReservationCollector
from ai_service.collectors.session_collector import SessionCollector
from ai_service.repositories.occupancy_repository import OccupancyRepository
from ai_service.repositories.reservation_repository import ReservationRepository
from ai_service.repositories.session_repository import ParkingSessionRepository
from ai_service.schemas.collector import CollectionSummary, CollectorStatusResponse
from ai_service.scheduler.scheduler import collection_scheduler

logger = logging.getLogger(__name__)


class CollectorService:
    """
    Service layer coordinating collection runs and reporting pipeline status.
    """

    def __init__(self, backend_client: BackendAPIClient) -> None:
        self.backend_client = backend_client

    async def run_all_collectors(
        self, db_session: AsyncSession
    ) -> Dict[str, CollectionSummary]:
        """
        Manually triggers all data collectors sequentially.
        Returns summaries for occupancy, reservations, and sessions.
        """
        logger.info("Manual trigger of all data collectors initiated.")

        occupancy_collector = OccupancyCollector(self.backend_client)
        reservation_collector = ReservationCollector(self.backend_client)
        session_collector = SessionCollector(self.backend_client)

        results: Dict[str, CollectionSummary] = {}

        # 1. Occupancy
        occ_summary = await occupancy_collector.collect(db_session)
        results[occupancy_collector.name] = occ_summary

        # 2. Reservations
        res_summary = await reservation_collector.collect(db_session)
        results[reservation_collector.name] = res_summary

        # 3. Parking Sessions
        sess_summary = await session_collector.collect(db_session)
        results[session_collector.name] = sess_summary

        # Update global scheduler state with manual run results
        collection_scheduler.last_summaries.update(results)
        if occ_summary.timestamp:
            collection_scheduler.last_run_time = occ_summary.timestamp

        logger.info("Manual trigger of all collectors completed successfully.")
        return results

    async def get_status(
        self, db_session: AsyncSession
    ) -> CollectorStatusResponse:
        """
        Retrieves complete pipeline status including database record counts, scheduler state, and last collection time.
        """
        occ_repo = OccupancyRepository(db_session)
        res_repo = ReservationRepository(db_session)
        sess_repo = ParkingSessionRepository(db_session)

        total_occ = await occ_repo.count()
        total_res = await res_repo.count()
        total_sess = await sess_repo.count()

        return CollectorStatusResponse(
            scheduler_status=collection_scheduler.status,
            last_collection_time=collection_scheduler.last_run_time,
            total_records={
                "occupancy": total_occ,
                "reservations": total_res,
                "sessions": total_sess,
            },
            last_summaries=collection_scheduler.last_summaries,
        )
