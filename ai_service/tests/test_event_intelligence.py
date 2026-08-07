"""
Unit and integration tests for Event-Aware Intelligence module.
"""

import os
import unittest
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from ai_service.main import app
from ai_service.database.session import get_db_session
from ai_service.database.base import Base
from ai_service.models.event import Event
from ai_service.models.occupancy import OccupancyHistory
from ai_service.services.event_impact_engine import EventImpactEngine
from ai_service.services.event_service import EventIntelligenceService
from ai_service.schemas.event import EventCreate, EventLocation, EventUpdate

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


class TestEventIntelligence(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        app.dependency_overrides[get_db_session] = override_get_db_session
        self.service = EventIntelligenceService()

        # Seed standard facility in DB
        async with AsyncSessionLocalTest() as db:
            occ = OccupancyHistory(
                facility_id="1",
                total_slots=100,
                occupied_slots=40,
                available_slots=60,
                occupancy_percentage=40.0,
                collected_at=datetime.now(timezone.utc),
            )
            db.add(occ)
            await db.commit()

    async def asyncTearDown(self) -> None:
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine_test.dispose()
        app.dependency_overrides.clear()

    def test_impact_engine_distance_calculation(self):
        """Test simple Haversine formula calculation."""
        # Distance between coordinates
        dist = EventImpactEngine.calculate_distance_km(12.9716, 77.5946, 12.9716, 77.5946)
        self.assertEqual(dist, 0.0)

        # Distance to near point
        dist_near = EventImpactEngine.calculate_distance_km(12.9716, 77.5946, 12.9750, 77.5990)
        self.assertGreater(dist_near, 0.0)
        self.assertLess(dist_near, 5.0)

    def test_impact_engine_time_weight(self):
        """Test time weight ramp up, plateau, and ramp down."""
        now = datetime.now(timezone.utc)
        start = now + timedelta(hours=2)
        end = now + timedelta(hours=4)

        # Active time during the event
        weight_during = EventImpactEngine.get_time_weight(start, end, now + timedelta(hours=3))
        self.assertEqual(weight_during, 1.0)

        # Active time before event (ramp up)
        weight_before = EventImpactEngine.get_time_weight(start, end, now + timedelta(hours=1))
        self.assertGreater(weight_before, 0.0)
        self.assertLess(weight_before, 1.0)

        # Active time after event (ramp down)
        weight_after = EventImpactEngine.get_time_weight(start, end, now + timedelta(hours=5))
        self.assertGreater(weight_after, 0.0)
        self.assertLess(weight_after, 1.0)

        # Way outside the window
        weight_out = EventImpactEngine.get_time_weight(start, end, now + timedelta(hours=8))
        self.assertEqual(weight_out, 0.0)

    async def test_event_crud_lifecycle(self):
        """Test complete event database lifecycle operations."""
        async with AsyncSessionLocalTest() as db:
            now = datetime.now(timezone.utc)
            event_in = EventCreate(
                name="Test Concert",
                type="Concert",
                location=EventLocation(name="Arena", latitude=12.9716, longitude=77.5946, radius_of_influence=2.0),
                expected_attendance=15000,
                start_time=now + timedelta(hours=1),
                end_time=now + timedelta(hours=3),
                confidence_score=0.9,
            )

            # Create
            ev = await self.service.create_event(db, event_in)
            self.assertIsNotNone(ev.id)
            self.assertEqual(ev.name, "Test Concert")

            # Read detail
            ev_read = await self.service.get_event_by_id(db, ev.event_id)
            self.assertIsNotNone(ev_read)
            self.assertEqual(ev_read.name, "Test Concert")

            # Update
            ev_up = await self.service.update_event(
                db,
                ev.event_id,
                EventUpdate(name="Updated Test Concert", expected_attendance=18000)
            )
            self.assertEqual(ev_up.name, "Updated Test Concert")
            self.assertEqual(ev_up.expected_attendance, 18000)

            # List
            events = await self.service.get_events(db)
            self.assertEqual(len(events), 1)

            # Delete
            deleted = await self.service.delete_event(db, ev.event_id)
            self.assertTrue(deleted)
            ev_gone = await self.service.get_event_by_id(db, ev.event_id)
            self.assertIsNone(ev_gone)

    async def test_facility_impacts_estimation(self):
        """Test event impacts are correctly estimated when events are active."""
        async with AsyncSessionLocalTest() as db:
            now = datetime.now(timezone.utc)
            
            # Create active event centered at facility coordinates
            event_in = EventCreate(
                name="Big Derby Match",
                type="Sports Event",
                location=EventLocation(name="Stadium", latitude=12.9716, longitude=77.5946, radius_of_influence=2.0),
                expected_attendance=30000,
                start_time=now + timedelta(hours=1),
                end_time=now + timedelta(hours=3),
                confidence_score=1.0,
                predicted_extra_demand=35.0,
                congestion_multiplier=2.0,
            )
            await self.service.create_event(db, event_in)

            # Estimate composite impacts
            impacts = await self.service.get_composite_impact(db, "1", now + timedelta(hours=2))
            self.assertEqual(impacts["events_count"], 1)
            self.assertGreater(impacts["composite_extra_occupancy_percentage"], 0.0)
            self.assertGreater(impacts["composite_congestion_multiplier"], 1.0)
            self.assertEqual(impacts["expected_congestion_level"], "SEVERE")

    async def test_api_endpoints_success(self):
        """Test FastAPI endpoints respond successfully with expected status codes."""
        now = datetime.now(timezone.utc)
        event_payload = {
            "name": "Local Music Carnival",
            "type": "Concert",
            "location": {
                "name": "Town Ground",
                "latitude": 12.9730,
                "longitude": 77.5950,
                "radius_of_influence": 2.0,
            },
            "expected_attendance": 8000,
            "start_time": (now + timedelta(hours=2)).isoformat(),
            "end_time": (now + timedelta(hours=5)).isoformat(),
            "confidence_score": 0.85,
        }

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # POST /events
            resp = await ac.post("/events", json=event_payload)
            self.assertEqual(resp.status_code, 201)
            ev_id = resp.json()["event_id"]

            # GET /events
            list_resp = await ac.get("/events")
            self.assertEqual(list_resp.status_code, 200)
            self.assertGreater(len(list_resp.json()), 0)

            # GET /events/upcoming
            up_resp = await ac.get("/events/upcoming")
            self.assertEqual(up_resp.status_code, 200)

            # GET /events/active
            act_resp = await ac.get("/events/active")
            self.assertEqual(act_resp.status_code, 200)

            # GET /events/{id}
            detail_resp = await ac.get(f"/events/{ev_id}")
            self.assertEqual(detail_resp.status_code, 200)

            # GET /events/{id}/impact
            imp_resp = await ac.get(f"/events/{ev_id}/impact")
            self.assertEqual(imp_resp.status_code, 200)

            # GET /events/forecast
            fc_resp = await ac.get("/events/forecast?facility_id=1&horizon_minutes=15")
            self.assertEqual(fc_resp.status_code, 200)
            self.assertIn("adjusted_predicted_occupancy", fc_resp.json())

            # GET /events/recommendations
            rec_resp = await ac.get("/events/recommendations?user_latitude=12.9716&user_longitude=77.5946&eta_minutes=20")
            self.assertEqual(rec_resp.status_code, 200)

            # GET /events/analytics
            an_resp = await ac.get("/events/analytics")
            self.assertEqual(an_resp.status_code, 200)

            # POST /events/simulations
            sim_resp = await ac.post("/events/simulations?simulation_name=concert")
            self.assertEqual(sim_resp.status_code, 200)

            # DELETE /events/{id}
            del_resp = await ac.delete(f"/events/{ev_id}")
            self.assertEqual(del_resp.status_code, 204)
