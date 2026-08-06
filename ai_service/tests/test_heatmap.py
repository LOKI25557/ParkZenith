"""
Unit and integration tests for the AI Heatmap Intelligence module.
"""

import os
import unittest
from datetime import datetime, timedelta, timezone
import pandas as pd
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from ai_service.main import app
from ai_service.database.session import get_db_session
from ai_service.database.base import Base
from ai_service.models.occupancy import OccupancyHistory
from ai_service.analytics.heatmap_calculations import (
    calculate_density_score,
    calculate_occupancy_percentage,
    calculate_congestion_index,
    calculate_capacity_utilization,
    calculate_zone_utilization,
    calculate_color_intensity,
    get_congestion_level,
)
from ai_service.services.heatmap_service import HeatmapService

# Setup test DB URL
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


class TestHeatmapIntelligence(unittest.IsolatedAsyncioTestCase):
    """
    Test suite verifying heatmap calculations, service logic, historical resampling, and API endpoints.
    """

    async def asyncSetUp(self) -> None:
        """Sets up database tables and overrides dependencies."""
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        app.dependency_overrides[get_db_session] = override_get_db_session

        self.now = datetime.now(timezone.utc)
        self.facility_id = "FAC-HEAT-001"
        
        # Insert mock occupancy history data
        async with AsyncSessionLocalTest() as session:
            self.occupancy_data = [
                # Facility overall occupancy
                OccupancyHistory(
                    facility_id=self.facility_id,
                    zone_id=None,
                    total_slots=100,
                    occupied_slots=40,
                    available_slots=60,
                    occupancy_percentage=40.0,
                    collected_at=self.now - timedelta(hours=2),
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
                # Zone specific occupancy
                OccupancyHistory(
                    facility_id=self.facility_id,
                    zone_id="ZONE-A",
                    total_slots=50,
                    occupied_slots=20,
                    available_slots=30,
                    occupancy_percentage=40.0,
                    collected_at=self.now - timedelta(hours=2),
                ),
                OccupancyHistory(
                    facility_id=self.facility_id,
                    zone_id="ZONE-A",
                    total_slots=50,
                    occupied_slots=45,
                    available_slots=5,
                    occupancy_percentage=90.0,
                    collected_at=self.now - timedelta(hours=1),
                ),
                OccupancyHistory(
                    facility_id=self.facility_id,
                    zone_id="ZONE-B",
                    total_slots=50,
                    occupied_slots=20,
                    available_slots=30,
                    occupancy_percentage=40.0,
                    collected_at=self.now - timedelta(hours=2),
                ),
                OccupancyHistory(
                    facility_id=self.facility_id,
                    zone_id="ZONE-B",
                    total_slots=50,
                    occupied_slots=35,
                    available_slots=15,
                    occupancy_percentage=70.0,
                    collected_at=self.now - timedelta(hours=1),
                ),
            ]
            session.add_all(self.occupancy_data)
            await session.commit()

        self.service = HeatmapService()

    async def asyncTearDown(self) -> None:
        """Clean up tables."""
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        app.dependency_overrides.clear()

    def test_heatmap_calculations(self) -> None:
        """Test the mathematical calculations layer."""
        # 1. Density Score
        self.assertEqual(calculate_density_score(50, 100), 50.0)
        self.assertEqual(calculate_density_score(0, 100), 0.0)
        self.assertEqual(calculate_density_score(30, 0), 0.0)

        # 2. Occupancy Percentage
        self.assertEqual(calculate_occupancy_percentage(75, 100), 75.0)

        # 3. Congestion Index
        # Formula: occ_pct * 0.8 + min(20.0, queue_length * 2.0 + waiting_time * 0.5)
        # With 80% occupancy, 0 queue length, 0 wait time: 80 * 0.8 = 64.0
        self.assertEqual(calculate_congestion_index(80, 100, 0.0, 0.0), 64.0)
        # With 80% occupancy, 5 queue length, 10 wait time: 80 * 0.8 + min(20.0, 10.0 + 5.0) = 64.0 + 15.0 = 79.0
        self.assertEqual(calculate_congestion_index(80, 100, 5.0, 10.0), 79.0)

        # 4. Utilization & Intensity
        self.assertEqual(calculate_capacity_utilization(90, 100), 90.0)
        self.assertEqual(calculate_zone_utilization(10, 50), 20.0)
        self.assertEqual(calculate_color_intensity(82.5), 82.5)

        # 5. Congestion Level
        self.assertEqual(get_congestion_level(10, 100, 0.0, 0.0), "LOW")
        self.assertEqual(get_congestion_level(96, 100, 0.0, 0.0), "SEVERE")

    async def test_heatmap_service_live(self) -> None:
        """Test service calculations for live heatmaps."""
        async with AsyncSessionLocalTest() as session:
            live = await self.service.get_live_heatmap(session)
            self.assertIsNotNone(live)
            self.assertTrue(len(live.facilities) > 0)
            
            # Check FAC-HEAT-001 specific live data
            fac_heat = next((f for f in live.facilities if f.facility_id == self.facility_id), None)
            self.assertIsNotNone(fac_heat)
            self.assertEqual(fac_heat.facility_id, self.facility_id)
            self.assertEqual(fac_heat.overall_density, 80.0)  # Latest overall record has 80 slots occupied
            self.assertEqual(fac_heat.overall_congestion_score.congestion_level, "MODERATE")  # 80% occupancy is classified as MODERATE

            self.assertTrue(len(fac_heat.points) > 0)
            self.assertTrue(len(fac_heat.zones) > 0)

    async def test_heatmap_service_history(self) -> None:
        """Test pandas historical resampling calculations."""
        async with AsyncSessionLocalTest() as session:
            start_date = self.now - timedelta(days=2)
            end_date = self.now + timedelta(days=1)
            
            history = await self.service.get_historical_heatmap(
                db=session,
                start_time=start_date,
                end_time=end_date,
                interval="hourly",
                facility_id=self.facility_id
            )
            self.assertIsNotNone(history)
            self.assertEqual(history.interval, "hourly")
            self.assertTrue(len(history.facilities) > 0)
            
            fac = history.facilities[0]
            self.assertEqual(fac.facility_id, self.facility_id)
            # Averages of occupied slots: (40 + 80) / 2 = 60. Averages of total slots: 100.
            # Average density should be 60.0%
            self.assertEqual(fac.overall_density, 60.0)

    async def test_heatmap_service_analytics(self) -> None:
        """Test zone-specific congestion analytics and summaries."""
        async with AsyncSessionLocalTest() as session:
            analytics = await self.service.get_zone_analytics(
                db=session,
                facility_id=self.facility_id,
                start_date=self.now - timedelta(days=2),
                end_date=self.now + timedelta(days=1)
            )
            self.assertIsNotNone(analytics)
            # Zone-A has (40 + 90) / 2 = 65. Zone-B has (40 + 70) / 2 = 55.
            # Zone-A should be the most congested zone
            self.assertIn("ZONE-A", analytics.most_congested_zones)
            self.assertIn("ZONE-B", analytics.least_occupied_zones)
            self.assertTrue(len(analytics.peak_congestion_periods) > 0)
            self.assertIn("most_congested", analytics.heatmap_summaries)

    async def test_api_routes(self) -> None:
        """Test the Heatmap API REST endpoints."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. GET /heatmap
            response = await client.get("/heatmap")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("timestamp", data)
            self.assertIn("facilities", data)

            # 2. GET /heatmap/live
            response = await client.get("/heatmap/live")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(len(data["facilities"]) > 0)

            # 3. GET /heatmap/history
            response = await client.get(f"/heatmap/history?facility_id={self.facility_id}&interval=hourly")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["interval"], "hourly")

            # 4. GET /heatmap/zones
            response = await client.get(f"/heatmap/zones?facility_id={self.facility_id}")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("most_congested_zones", data)
            self.assertIn("least_occupied_zones", data)

            # 5. GET /heatmap/facility/{facility_id}
            response = await client.get(f"/heatmap/facility/{self.facility_id}")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["facility_id"], self.facility_id)

            # 6. GET /heatmap/facility/{non_existent_id} -> 404
            response = await client.get("/heatmap/facility/FAC-UNKNOWN")
            self.assertEqual(response.status_code, 404)
