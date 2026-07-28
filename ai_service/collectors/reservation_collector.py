"""
Reservation Collector module.
Fetches, validates, deduplicates, and stores parking reservation data.
"""

import logging
from datetime import datetime, timezone
from typing import List, Set
from sqlalchemy.ext.asyncio import AsyncSession

from ai_service.collectors.base import BaseCollector
from ai_service.utils.backend_client import BackendAPIClient
from ai_service.repositories.reservation_repository import ReservationRepository
from ai_service.models.reservation import ReservationHistory
from ai_service.schemas.reservation import ReservationHistoryCreate
from ai_service.schemas.collector import CollectionSummary
from ai_service.core.exceptions import BackendUnavailableError, DatabaseError

logger = logging.getLogger("ai_service.collector.reservation")


class ReservationCollector(BaseCollector):
    """
    Collector responsible for periodic ingestion of reservation history.
    """

    @property
    def name(self) -> str:
        return "ReservationCollector"

    async def collect(self, session: AsyncSession) -> CollectionSummary:
        """
        Runs the reservation data collection process.
        """
        start_time = datetime.now(timezone.utc)
        logger.info("[%s] Starting reservation data collection cycle.", self.name)

        summary = CollectionSummary(
            collector_name=self.name,
            status="SUCCESS",
            timestamp=start_time,
        )

        try:
            # 1. Fetch data from backend API
            raw_records: List[ReservationHistoryCreate] = (
                await self.backend_client.fetch_reservations_history()
            )
            summary.fetched_count = len(raw_records)
            logger.info(
                "[%s] Retrieved %d reservation records from backend.",
                self.name,
                summary.fetched_count,
            )

            if not raw_records:
                summary.message = "No new reservation records provided by backend."
                return summary

            repo = ReservationRepository(session)

            # 2. Extract reservation_ids and check DB for existing records
            fetched_res_ids = [r.reservation_id for r in raw_records]
            existing_ids: Set[str] = await repo.get_existing_reservation_ids(fetched_res_ids)

            models_to_insert: List[ReservationHistory] = []
            seen_in_batch: Set[str] = set()

            for item in raw_records:
                res_id = item.reservation_id

                # Deduplicate against DB & batch
                if res_id in existing_ids or res_id in seen_in_batch:
                    summary.duplicate_count += 1
                    continue

                seen_in_batch.add(res_id)

                models_to_insert.append(
                    ReservationHistory(
                        reservation_id=item.reservation_id,
                        facility_id=item.facility_id,
                        slot_id=item.slot_id,
                        reservation_status=item.reservation_status,
                        reservation_start=item.reservation_start,
                        reservation_end=item.reservation_end,
                        duration_minutes=item.duration_minutes,
                        collected_at=item.collected_at or datetime.now(timezone.utc),
                    )
                )

            # 3. Store new records
            if models_to_insert:
                saved = await repo.save_many(models_to_insert)
                summary.inserted_count = len(saved)
                logger.info(
                    "[%s] Successfully stored %d new reservation records (%d duplicates ignored).",
                    self.name,
                    summary.inserted_count,
                    summary.duplicate_count,
                )
            else:
                logger.info(
                    "[%s] All %d fetched reservation records were duplicates. 0 inserted.",
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
