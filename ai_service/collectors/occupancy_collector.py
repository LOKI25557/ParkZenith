"""
Occupancy Collector module.
Fetches, validates, deduplicates, and stores facility occupancy data.
"""

import logging
from datetime import datetime, timezone
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from ai_service.collectors.base import BaseCollector
from ai_service.utils.backend_client import BackendAPIClient
from ai_service.repositories.occupancy_repository import OccupancyRepository
from ai_service.models.occupancy import OccupancyHistory
from ai_service.schemas.occupancy import OccupancyHistoryCreate
from ai_service.schemas.collector import CollectionSummary
from ai_service.core.exceptions import BackendUnavailableError, DatabaseError

logger = logging.getLogger("ai_service.collector.occupancy")


class OccupancyCollector(BaseCollector):
    """
    Collector responsible for periodic ingestion of occupancy history.
    """

    @property
    def name(self) -> str:
        return "OccupancyCollector"

    async def collect(self, session: AsyncSession) -> CollectionSummary:
        """
        Runs the occupancy data collection process.
        """
        start_time = datetime.now(timezone.utc)
        logger.info("[%s] Starting occupancy data collection cycle.", self.name)

        summary = CollectionSummary(
            collector_name=self.name,
            status="SUCCESS",
            timestamp=start_time,
        )

        try:
            # 1. Fetch data from backend API
            raw_records: List[OccupancyHistoryCreate] = (
                await self.backend_client.fetch_occupancy_history()
            )
            summary.fetched_count = len(raw_records)
            logger.info(
                "[%s] Retrieved %d occupancy records from backend.",
                self.name,
                summary.fetched_count,
            )

            if not raw_records:
                summary.message = "No new occupancy records provided by backend."
                return summary

            repo = OccupancyRepository(session)

            # 2. Get latest stored occupancy records to prevent saving identical duplicates
            latest_records = await repo.get_latest(limit=50)
            def _fmt(dt):
                return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else ""

            existing_snapshots = {
                (r.facility_id, r.zone_id, _fmt(r.collected_at))
                for r in latest_records
            }

            models_to_insert: List[OccupancyHistory] = []
            seen_in_batch = set()

            for item in raw_records:
                ts_str = _fmt(item.collected_at)
                snapshot_key = (item.facility_id, item.zone_id, ts_str)

                # Deduplicate against batch & existing snapshots
                if snapshot_key in existing_snapshots or snapshot_key in seen_in_batch:
                    summary.duplicate_count += 1
                    continue

                seen_in_batch.add(snapshot_key)

                models_to_insert.append(
                    OccupancyHistory(
                        facility_id=item.facility_id,
                        zone_id=item.zone_id,
                        total_slots=item.total_slots,
                        occupied_slots=item.occupied_slots,
                        available_slots=item.available_slots,
                        occupancy_percentage=item.occupancy_percentage,
                        collected_at=item.collected_at or datetime.now(timezone.utc),
                    )
                )

            # 3. Store new records
            if models_to_insert:
                saved = await repo.save_many(models_to_insert)
                summary.inserted_count = len(saved)
                logger.info(
                    "[%s] Successfully stored %d new occupancy records (%d duplicates ignored).",
                    self.name,
                    summary.inserted_count,
                    summary.duplicate_count,
                )
            else:
                logger.info(
                    "[%s] All %d fetched records were duplicates. 0 inserted.",
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
