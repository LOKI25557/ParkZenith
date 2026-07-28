"""
Parking Session Collector module.
Fetches, validates, deduplicates, and stores parking session data.
"""

import logging
from datetime import datetime, timezone
from typing import List, Set
from sqlalchemy.ext.asyncio import AsyncSession

from ai_service.collectors.base import BaseCollector
from ai_service.utils.backend_client import BackendAPIClient
from ai_service.repositories.session_repository import ParkingSessionRepository
from ai_service.models.session import ParkingSessionHistory
from ai_service.schemas.session import ParkingSessionHistoryCreate
from ai_service.schemas.collector import CollectionSummary
from ai_service.core.exceptions import BackendUnavailableError, DatabaseError

logger = logging.getLogger("ai_service.collector.session")


class SessionCollector(BaseCollector):
    """
    Collector responsible for periodic ingestion of parking session history.
    """

    @property
    def name(self) -> str:
        return "SessionCollector"

    async def collect(self, session: AsyncSession) -> CollectionSummary:
        """
        Runs the parking session data collection process.
        """
        start_time = datetime.now(timezone.utc)
        logger.info("[%s] Starting parking session data collection cycle.", self.name)

        summary = CollectionSummary(
            collector_name=self.name,
            status="SUCCESS",
            timestamp=start_time,
        )

        try:
            # 1. Fetch data from backend API
            raw_records: List[ParkingSessionHistoryCreate] = (
                await self.backend_client.fetch_sessions_history()
            )
            summary.fetched_count = len(raw_records)
            logger.info(
                "[%s] Retrieved %d parking session records from backend.",
                self.name,
                summary.fetched_count,
            )

            if not raw_records:
                summary.message = "No new parking session records provided by backend."
                return summary

            repo = ParkingSessionRepository(session)

            # 2. Extract session_ids and check DB for existing records
            fetched_sess_ids = [r.session_id for r in raw_records]
            existing_ids: Set[str] = await repo.get_existing_session_ids(fetched_sess_ids)

            models_to_insert: List[ParkingSessionHistory] = []
            seen_in_batch: Set[str] = set()

            for item in raw_records:
                sess_id = item.session_id

                # Deduplicate against DB & batch
                if sess_id in existing_ids or sess_id in seen_in_batch:
                    summary.duplicate_count += 1
                    continue

                seen_in_batch.add(sess_id)

                models_to_insert.append(
                    ParkingSessionHistory(
                        session_id=item.session_id,
                        facility_id=item.facility_id,
                        vehicle_type=item.vehicle_type,
                        check_in_time=item.check_in_time,
                        check_out_time=item.check_out_time,
                        duration_minutes=item.duration_minutes,
                        parking_fee=item.parking_fee,
                        collected_at=item.collected_at or datetime.now(timezone.utc),
                    )
                )

            # 3. Store new records
            if models_to_insert:
                saved = await repo.save_many(models_to_insert)
                summary.inserted_count = len(saved)
                logger.info(
                    "[%s] Successfully stored %d new parking session records (%d duplicates ignored).",
                    self.name,
                    summary.inserted_count,
                    summary.duplicate_count,
                )
            else:
                logger.info(
                    "[%s] All %d fetched parking session records were duplicates. 0 inserted.",
                    self.name,
                    summary.fetched_count,
                )

            summary.message = (
                f"Collection complete: {summary.inserted_count} inserted, "
                f"{summary.duplicate_count} duplicates skipped."
            )
            return summary

        except BackendUnavailableError as exc:
            logger.error("[%s] Backend API unavailable: %s", self.name, str(exc))
            summary.status = "ERROR"
            summary.message = f"Backend unavailable: {exc.message}"
            return summary
        except Exception as exc:
            logger.exception("[%s] Unexpected failure during collection: %s", self.name, str(exc))
            summary.status = "ERROR"
            summary.message = f"Collection failed: {str(exc)}"
            return summary
