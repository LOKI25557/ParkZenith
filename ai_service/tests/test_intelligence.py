"""
Unit and integration tests for the Unified AI Intelligence Orchestrator.
"""

import unittest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from ai_service.main import app
from ai_service.database.session import get_db_session
from ai_service.database.base import Base
from ai_service.models.occupancy import OccupancyHistory
from ai_service.models.reservation import ReservationHistory
from ai_service.models.session import ParkingSessionHistory
from ai_service.services.intelligence_service import IntelligenceService

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


class TestIntelligenceOrchestrator(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        app.dependency_overrides[get_db_session] = override_get_db_session

        # Seed data for a facility
        async with AsyncSessionLocalTest() as session:
            now = datetime.now(timezone.utc)
            # Seed occupancy history
            for offset in range(5):
                session.add(
                    OccupancyHistory(
                        facility_id="1",
                        zone_id="ZONE-A",
                        total_slots=100,
                        occupied_slots=80,
                        available_slots=20,
                        occupancy_percentage=80.0,
                        collected_at=now - timedelta(minutes=15 * offset),
                    )
                )
                # Seed another facility to act as alternative
                session.add(
                    OccupancyHistory(
                        facility_id="2",
                        zone_id="ZONE-A",
                        total_slots=150,
                        occupied_slots=30,
                        available_slots=120,
                        occupancy_percentage=20.0,
                        collected_at=now - timedelta(minutes=15 * offset),
                    )
                )

            # Seed parking sessions
            for i in range(15):
                session.add(
                    ParkingSessionHistory(
                        session_id=f"SESS-{i}",
                        facility_id="1",
                        vehicle_type="CAR",
                        check_in_time=now - timedelta(hours=i),
                        check_out_time=now - timedelta(hours=i) + timedelta(minutes=45),
                        duration_minutes=45,
                        parking_fee=5.0,
                        collected_at=now
                    )
                )
                session.add(
                    ParkingSessionHistory(
                        session_id=f"SESS-ALT-{i}",
                        facility_id="2",
                        vehicle_type="CAR",
                        check_in_time=now - timedelta(hours=i),
                        check_out_time=now - timedelta(hours=i) + timedelta(minutes=45),
                        duration_minutes=45,
                        parking_fee=5.0,
                        collected_at=now
                    )
                )

            await session.commit()

    async def asyncTearDown(self) -> None:
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine_test.dispose()
        app.dependency_overrides.clear()

    async def test_intelligence_orchestrator_get_decision(self) -> None:
        """Test unified decision scoring and reasoning in IntelligenceService."""
        service = IntelligenceService()
        async with AsyncSessionLocalTest() as session:
            res = await service.get_decision(
                db=session,
                facility_id="1",
                eta_minutes=20,
                latitude=12.9716,
                longitude=77.5946,
            )
            
            self.assertEqual(res["facility_id"], "1")
            self.assertEqual(res["eta_minutes"], 20)
            self.assertIn("predicted_occupancy", res)
            self.assertIn("predicted_available_slots", res)
            self.assertIn("availability_probability", res)
            self.assertIn("queue_wait_minutes", res)
            self.assertIn("confidence", res)
            self.assertIn("recommendation", res)
            self.assertIn("reasoning", res)
            self.assertIn("prediction_status", res)
            
            # Since occupancy is 80%, recommendation should be LIMITED or HIGH_DEMAND
            self.assertNotEqual(res["recommendation"], "GOOD_CHOICE")
            self.assertTrue(len(res["alternative_facilities"]) > 0)
            
            # Check alternative list includes facility '2'
            alt_ids = [alt["facility_id"] for alt in res["alternative_facilities"]]
            self.assertIn("2", alt_ids)

    async def test_intelligence_api_endpoint(self) -> None:
        """Test posting to /intelligence/decision endpoint works successfully."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            req_body = {
                "facility_id": "1",
                "eta_minutes": 20,
                "latitude": 12.9716,
                "longitude": 77.5946,
            }
            res = await ac.post("/intelligence/decision", json=req_body)
            self.assertEqual(res.status_code, 200)
            
            data = res.json()
            self.assertEqual(data["facility_id"], "1")
            self.assertEqual(data["eta_minutes"], 20)
            self.assertIn("recommendation", data)
            self.assertIn("reasoning", data)
            self.assertIn("alternative_facilities", data)
            self.assertTrue(len(data["alternative_facilities"]) > 0)

    async def test_intelligence_missing_facility(self) -> None:
        """Test intelligence endpoint returns 404 for missing facility ID."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            req_body = {
                "facility_id": "999",
                "eta_minutes": 20,
            }
            res = await ac.post("/intelligence/decision", json=req_body)
            self.assertEqual(res.status_code, 404)
