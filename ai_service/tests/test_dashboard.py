"""
Unit and functional tests for the AI Dashboard Analytics & Overview (Phase 12).
"""

import os
import unittest
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from ai_service.main import app
from ai_service.config.settings import settings
from ai_service.database.session import get_db_session
from ai_service.database.base import Base
from ai_service.models.occupancy import OccupancyHistory
from ai_service.models.reservation import ReservationHistory
from ai_service.models.session import ParkingSessionHistory
from ai_service.services.dashboard_service import DashboardService
from ai_service.schemas.dashboard import AIOverview

# Setup test database in memory
DATABASE_URL_TEST = "sqlite+aiosqlite:///:memory:"

engine_test = create_async_engine(
    DATABASE_URL_TEST,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

AsyncSessionLocalTest = async_sessionmaker(
    bind=engine_test,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def override_get_db_session():
    async with AsyncSessionLocalTest() as session:
        yield session


class TestAIDashboard(unittest.IsolatedAsyncioTestCase):
    """
    Test suite verifying the AI Dashboard Analytics & Final Intelligence Completion.
    """

    async def asyncSetUp(self) -> None:
        """Sets up database tables and initializes common mock data for dashboard tests."""
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        app.dependency_overrides[get_db_session] = override_get_db_session

        self.now = datetime.now(timezone.utc)
        self.facility_id = "1"
        self.zone_id = "ZONE-A"

        # Populate database with historical data for aggregation
        async with AsyncSessionLocalTest() as session:
            # 1. Occupancy History
            occupancies = [
                OccupancyHistory(
                    facility_id=self.facility_id,
                    zone_id=None,  # Facility-level
                    total_slots=100,
                    occupied_slots=45,
                    available_slots=55,
                    occupancy_percentage=45.0,
                    collected_at=self.now - timedelta(hours=3),
                ),
                OccupancyHistory(
                    facility_id=self.facility_id,
                    zone_id=self.zone_id,  # Zone-level
                    total_slots=50,
                    occupied_slots=25,
                    available_slots=25,
                    occupancy_percentage=50.0,
                    collected_at=self.now - timedelta(hours=3),
                ),
                OccupancyHistory(
                    facility_id=self.facility_id,
                    zone_id=None,
                    total_slots=100,
                    occupied_slots=80,
                    available_slots=20,
                    occupancy_percentage=80.0,
                    collected_at=self.now - timedelta(hours=1),
                ),
            ]
            session.add_all(occupancies)

            # 2. Reservation History
            reservations = [
                ReservationHistory(
                    reservation_id="RES-01",
                    facility_id=self.facility_id,
                    slot_id="SLOT-01",
                    reservation_status="COMPLETED",
                    reservation_start=self.now - timedelta(hours=2),
                    reservation_end=self.now - timedelta(hours=1),
                    duration_minutes=60.0,
                    collected_at=self.now,
                )
            ]
            session.add_all(reservations)

            # 3. Parking Session History
            sessions = [
                ParkingSessionHistory(
                    session_id="SESS-01",
                    facility_id=self.facility_id,
                    vehicle_type="CAR",
                    check_in_time=self.now - timedelta(hours=2),
                    check_out_time=self.now - timedelta(hours=1),
                    duration_minutes=60.0,
                    parking_fee=10.0,
                    collected_at=self.now,
                )
            ]
            session.add_all(sessions)
            await session.commit()

        self.service = DashboardService()

    async def asyncTearDown(self) -> None:
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine_test.dispose()
        app.dependency_overrides.clear()

    async def test_dashboard_service_aggregation(self):
        """Test that the DashboardService aggregates data correctly from all sub-services."""
        async with AsyncSessionLocalTest() as session:
            dashboard = await self.service.get_dashboard(
                db=session,
                facility_id=self.facility_id,
                eta_minutes=20,
                latitude=12.9716,
                longitude=77.5946,
            )

            # Assert top-level sections exist
            self.assertIn("occupancy", dashboard)
            self.assertIn("forecast", dashboard)
            self.assertIn("availability", dashboard)
            self.assertIn("recommendations", dashboard)
            self.assertIn("queue", dashboard)
            self.assertIn("heatmap", dashboard)
            self.assertIn("events", dashboard)
            self.assertIn("insights", dashboard)
            self.assertIn("summary", dashboard)

            # Assert occupancy section
            occ = dashboard["occupancy"]
            self.assertEqual(occ["facility_id"], self.facility_id)
            self.assertEqual(occ["total_capacity"], 100)
            self.assertEqual(occ["occupied_spaces"], 80)
            self.assertEqual(occ["available_spaces"], 20)

            # Assert availability
            avail = dashboard["availability"]
            self.assertEqual(avail["eta_minutes"], 20)
            self.assertGreaterEqual(avail["arrival_availability_probability"], 0.0)

            # Assert queue
            q = dashboard["queue"]
            self.assertGreaterEqual(q["predicted_waiting_time"], 0.0)

            # Assert insights are generated deterministically
            self.assertGreater(len(dashboard["insights"]), 0)
            for insight in dashboard["insights"]:
                self.assertIn("type", insight)
                self.assertIn("severity", insight)
                self.assertIn("message", insight)

    async def test_dashboard_api_endpoint(self):
        """Test the GET /ai/dashboard endpoint functionality and response validation."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.get(
                "/ai/dashboard",
                params={
                    "facility_id": self.facility_id,
                    "eta_minutes": 15,
                    "latitude": 12.9716,
                    "longitude": 77.5946,
                },
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            
            # Validate response schema using Pydantic model
            overview = AIOverview(**data)
            self.assertEqual(overview.occupancy.facility_id, self.facility_id)
            self.assertEqual(overview.availability.eta_minutes, 15)
            self.assertGreater(len(overview.insights), 0)

    async def test_dashboard_graceful_degradation(self):
        """Test that the dashboard service degrades gracefully on partial-service failures."""
        # Create a dashboard request for a non-existent facility
        async with AsyncSessionLocalTest() as session:
            # Requesting dashboard for facility "999" should degrade gracefully
            # or return default fallback overview instead of throwing exceptions.
            dashboard = await self.service.get_dashboard(
                db=session,
                facility_id="999",
                eta_minutes=20,
            )
            self.assertEqual(dashboard["occupancy"]["facility_id"], "999")
            self.assertEqual(dashboard["occupancy"]["occupied_spaces"], 0)
            self.assertEqual(dashboard["forecast"]["forecast_30m"], 0.0)
            self.assertEqual(dashboard["queue"]["predicted_waiting_time"], 0.0)
            self.assertEqual(dashboard["summary"]["status"], "NORMAL")
