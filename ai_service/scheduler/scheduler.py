"""
APScheduler wrapper for periodic collection jobs in FastAPI.
Handles background job scheduling, execution tracking, and graceful shutdown.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ai_service.config.settings import settings
from ai_service.database.session import AsyncSessionFactory
from ai_service.utils.backend_client import BackendAPIClient
from ai_service.collectors.occupancy_collector import OccupancyCollector
from ai_service.collectors.reservation_collector import ReservationCollector
from ai_service.collectors.session_collector import SessionCollector
from ai_service.schemas.collector import CollectionSummary

logger = logging.getLogger("ai_service.scheduler")


class CollectionScheduler:
    """
    Manages background periodic data collection jobs using APScheduler.
    """

    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler(timezone="UTC")
        self.last_run_time: Optional[datetime] = None
        self.last_summaries: Dict[str, CollectionSummary] = {}
        self._is_running = False

    async def _run_job_wrapper(self, collector_cls: Any) -> None:
        """
        Job execution wrapper that acquires an async DB session and executes a collector.
        """
        async with AsyncSessionFactory() as db_session:
            backend_client = BackendAPIClient()
            collector = collector_cls(backend_client)
            try:
                summary = await collector.collect(db_session)
                await db_session.commit()

                self.last_run_time = datetime.now(timezone.utc)
                self.last_summaries[collector.name] = summary
                logger.info("[%s] Scheduled job finished: %s", collector.name, summary.message)
            except Exception as exc:
                await db_session.rollback()
                logger.exception("[%s] Scheduled job failed: %s", collector.name, str(exc))

    def start(self) -> None:
        """
        Starts the background scheduler and registers periodic jobs.
        """
        if self._is_running:
            logger.warning("Scheduler is already running.")
            return

        logger.info("Starting background collection scheduler...")

        # 1. Occupancy Collection Job (Default: every 60s)
        self.scheduler.add_job(
            self._run_job_wrapper,
            trigger=IntervalTrigger(seconds=settings.OCCUPANCY_COLLECTION_INTERVAL_SECONDS),
            args=[OccupancyCollector],
            id="occupancy_collector_job",
            name="Occupancy Data Collection Job",
            replace_existing=True,
            max_instances=1,
        )

        # 2. Reservation Collection Job (Default: every 300s)
        self.scheduler.add_job(
            self._run_job_wrapper,
            trigger=IntervalTrigger(seconds=settings.RESERVATION_COLLECTION_INTERVAL_SECONDS),
            args=[ReservationCollector],
            id="reservation_collector_job",
            name="Reservation Data Collection Job",
            replace_existing=True,
            max_instances=1,
        )

        # 3. Parking Session Collection Job (Default: every 300s)
        self.scheduler.add_job(
            self._run_job_wrapper,
            trigger=IntervalTrigger(seconds=settings.SESSION_COLLECTION_INTERVAL_SECONDS),
            args=[SessionCollector],
            id="session_collector_job",
            name="Parking Session Data Collection Job",
            replace_existing=True,
            max_instances=1,
        )

        self.scheduler.start()
        self._is_running = True
        logger.info("Background collection scheduler started successfully.")

    def shutdown(self) -> None:
        """
        Shuts down the scheduler gracefully.
        """
        if self._is_running and self.scheduler.running:
            logger.info("Stopping background collection scheduler...")
            self.scheduler.shutdown(wait=False)
            self._is_running = False
            logger.info("Scheduler stopped.")

    @property
    def status(self) -> str:
        """
        Returns scheduler status string.
        """
        if self.scheduler.running:
            return "RUNNING"
        return "STOPPED"


# Global singleton instance
collection_scheduler = CollectionScheduler()
