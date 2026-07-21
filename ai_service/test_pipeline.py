"""
Standalone verification script for ParkZenith AI Service Phase 1 Pipeline.
Tests async DB initialization, repositories, collectors with deduplication, and Pandas dataset exports.
"""

import asyncio
import os
import shutil
import unittest
from datetime import datetime, timedelta, timezone

from ai_service.config.settings import settings
from ai_service.database.session import engine, init_db, AsyncSessionFactory
from ai_service.database.base import Base
from ai_service.models.occupancy import OccupancyHistory
from ai_service.models.reservation import ReservationHistory
from ai_service.models.session import ParkingSessionHistory
from ai_service.schemas.occupancy import OccupancyHistoryCreate
from ai_service.schemas.reservation import ReservationHistoryCreate
from ai_service.schemas.session import ParkingSessionHistoryCreate
from ai_service.repositories.occupancy_repository import OccupancyRepository
from ai_service.repositories.reservation_repository import ReservationRepository
from ai_service.repositories.session_repository import ParkingSessionRepository
from ai_service.collectors.occupancy_collector import OccupancyCollector
from ai_service.collectors.reservation_collector import ReservationCollector
from ai_service.collectors.session_collector import SessionCollector
from ai_service.utils.dataset_exporter import DatasetExporter


class MockBackendAPIClient:
    """Mock HTTP client simulating backend responses."""

    def __init__(self):
        self.now = datetime.now(timezone.utc)

    async def fetch_occupancy_history(self, limit=500):
        return [
            OccupancyHistoryCreate(
                facility_id="FAC-TEST",
                zone_id="ZONE-A",
                total_slots=100,
                occupied_slots=45,
                available_slots=55,
                occupancy_percentage=45.0,
                collected_at=self.now,
            ),
            OccupancyHistoryCreate(
                facility_id="FAC-TEST",
                zone_id="ZONE-B",
                total_slots=50,
                occupied_slots=20,
                available_slots=30,
                occupancy_percentage=40.0,
                collected_at=self.now,
            ),
        ]

    async def fetch_reservations_history(self, limit=500):
        return [
            ReservationHistoryCreate(
                reservation_id="RES-001",
                facility_id="FAC-TEST",
                slot_id="SLOT-1",
                reservation_status="COMPLETED",
                reservation_start=self.now - timedelta(hours=2),
                reservation_end=self.now - timedelta(hours=1),
                duration_minutes=60.0,
                collected_at=self.now,
            ),
            ReservationHistoryCreate(
                reservation_id="RES-002",
                facility_id="FAC-TEST",
                slot_id="SLOT-2",
                reservation_status="ACTIVE",
                reservation_start=self.now,
                reservation_end=self.now + timedelta(hours=1),
                duration_minutes=60.0,
                collected_at=self.now,
            ),
        ]

    async def fetch_sessions_history(self, limit=500):
        return [
            ParkingSessionHistoryCreate(
                session_id="SESS-001",
                facility_id="FAC-TEST",
                vehicle_type="CAR",
                check_in_time=self.now - timedelta(hours=3),
                check_out_time=self.now - timedelta(hours=1),
                duration_minutes=120.0,
                parking_fee=15.50,
                collected_at=self.now,
            ),
            ParkingSessionHistoryCreate(
                session_id="SESS-002",
                facility_id="FAC-TEST",
                vehicle_type="EV",
                check_in_time=self.now - timedelta(minutes=45),
                check_out_time=None,
                duration_minutes=None,
                parking_fee=None,
                collected_at=self.now,
            ),
        ]


class TestAIServicePipeline(unittest.IsolatedAsyncioTestCase):
    """Test suite for AI Service Data Pipeline."""

    async def asyncSetUp(self):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)


    async def test_01_repositories_and_collectors(self):
        mock_client = MockBackendAPIClient()

        async with AsyncSessionFactory() as session:
            # 1. Run Collectors
            occ_collector = OccupancyCollector(mock_client)
            res_collector = ReservationCollector(mock_client)
            sess_collector = SessionCollector(mock_client)

            occ_summary = await occ_collector.collect(session)
            self.assertEqual(occ_summary.status, "SUCCESS")
            self.assertEqual(occ_summary.inserted_count, 2)

            res_summary = await res_collector.collect(session)
            self.assertEqual(res_summary.status, "SUCCESS")
            self.assertEqual(res_summary.inserted_count, 2)

            sess_summary = await sess_collector.collect(session)
            self.assertEqual(sess_summary.status, "SUCCESS")
            self.assertEqual(sess_summary.inserted_count, 2)

            await session.commit()

            # 2. Test Deduplication by re-running collectors
            occ_summary2 = await occ_collector.collect(session)
            self.assertEqual(occ_summary2.inserted_count, 0)
            self.assertEqual(occ_summary2.duplicate_count, 2)

            res_summary2 = await res_collector.collect(session)
            self.assertEqual(res_summary2.inserted_count, 0)
            self.assertEqual(res_summary2.duplicate_count, 2)

            sess_summary2 = await sess_collector.collect(session)
            self.assertEqual(sess_summary2.inserted_count, 0)
            self.assertEqual(sess_summary2.duplicate_count, 2)

    async def test_02_csv_export(self):
        mock_client = MockBackendAPIClient()
        async with AsyncSessionFactory() as session:
            # First collect records into database
            await OccupancyCollector(mock_client).collect(session)
            await ReservationCollector(mock_client).collect(session)
            await SessionCollector(mock_client).collect(session)
            await session.commit()

            # Now test export
            exporter = DatasetExporter(export_dir="./test_datasets")
            summary = await exporter.export_all(session)
            self.assertEqual(summary["status"], "SUCCESS")
            for file_path in summary["exported_files"]:
                self.assertTrue(os.path.exists(file_path))

        # Cleanup test datasets directory
        if os.path.exists("./test_datasets"):
            shutil.rmtree("./test_datasets")


if __name__ == "__main__":
    unittest.main()
