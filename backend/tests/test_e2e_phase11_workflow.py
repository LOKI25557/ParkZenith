import asyncio
import unittest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from datetime import datetime, timedelta, timezone

from backend.app.main import app
from backend.app.database.session import get_async_session
from backend.app.models.base import Base
from backend.app.core.dependencies import get_current_user, get_admin_user
from backend.app.models.user import User
from backend.app.models.parking_facility import ParkingFacility
from backend.app.models.parking_zone import ParkingZone
from backend.app.models.parking_slot import ParkingSlot, ParkingSlotStatus
from backend.app.models.session import ParkingSession, ParkingSessionStatus
from backend.app.services.payment_service import payment_service
from backend.app.models.payment import PaymentStatus

DATABASE_URL_TEST = "sqlite+aiosqlite:///test_phase11_workflow.db"

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

async def override_get_async_session():
    async with AsyncSessionLocalTest() as session:
        yield session

async def override_get_current_user():
    return User(id=1, email="user@test.com", is_superuser=False)

async def override_get_admin_user():
    return User(id=2, email="admin@test.com", is_superuser=True)

import os

class TestE2EPhase11Workflow(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        if os.path.exists("test_phase11_workflow.db"):
            try:
                os.remove("test_phase11_workflow.db")
            except:
                pass
                
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        app.dependency_overrides[get_async_session] = override_get_async_session
        app.dependency_overrides[get_admin_user] = override_get_admin_user
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        # Setup mock data
        async with AsyncSessionLocalTest() as session:
            # We also need a user in the DB for payment service which queries it
            user = User(id=1, email="user@test.com", full_name="Test User", hashed_password="hashed")
            user2 = User(id=2, email="user2@test.com", full_name="Test User 2", hashed_password="hashed")
            session.add(user)
            session.add(user2)

            facility = ParkingFacility(name="E2E Facility", address="E2E Address", latitude=12.9, longitude=77.5, is_active=True, total_slots=5)
            session.add(facility)
            await session.commit()
            await session.refresh(facility)
            
            zone = ParkingZone(facility_id=facility.id, name="E2E Zone", total_slots=5)
            session.add(zone)
            await session.commit()
            await session.refresh(zone)
            
            slots = []
            for i in range(5):
                slot = ParkingSlot(zone_id=zone.id, slot_number=f"E2E-{i}", status=ParkingSlotStatus.AVAILABLE)
                slots.append(slot)
            
            session.add_all(slots)
            await session.commit()
            
            self.facility_id = facility.id
            self.slot_id = slots[0].id
            self.slot_id_2 = slots[1].id

    async def asyncTearDown(self) -> None:
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine_test.dispose()
        app.dependency_overrides.clear()

    @patch("backend.app.services.parking_intelligence_service.ai_service_client")
    async def test_full_user_journey_with_ai(self, mock_ai_client):
        # Setup AI mock
        mock_ai_client.get_recommendations = AsyncMock(return_value={
            "success": True,
            "data": {
                "recommendations": [
                    {
                        "rank": 1,
                        "facility_id": str(self.facility_id),
                        "facility_name": "E2E Facility",
                        "recommendation_score": 95.0,
                        "availability_probability": 0.8,
                        "forecast_occupancy": 50.0,
                        "distance_km": 1.5,
                        "walking_distance_m": 1500,
                        "estimated_cost": 20.0,
                        "queue_wait_minutes": 5.0,
                        "occupancy_risk": "LOW",
                        "confidence": 0.9,
                        "reason": "AI"
                    }
                ],
                "total_candidates": 1
            }
        })
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Discover parking / AI Request
            req = {"latitude": 12.9, "longitude": 77.5, "eta_minutes": 20}
            response = await ac.post("/api/v1/parking/recommend", json=req)
            if response.status_code == 404:
                response = await ac.post("/parking/recommend", json=req)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["returned_results"], 1)

            # 2. Reservation
            now = datetime.now(timezone.utc)
            start = now + timedelta(minutes=10)
            end = start + timedelta(hours=2)
            res_req = {
                "slot_id": self.slot_id,
                "reservation_start": start.isoformat(),
                "reservation_end": end.isoformat()
            }
            res = await ac.post("/api/v1/reservations", json=res_req)
            if res.status_code == 404:
                res = await ac.post("/reservations", json=res_req)
            self.assertEqual(res.status_code, 201)
            reservation_id = res.json()["id"]

            # 3. Start Session (simulate arrival)
            sess_req = {"slot_id": self.slot_id, "reservation_id": reservation_id}
            res = await ac.post("/api/v1/sessions/start", json=sess_req)
            if res.status_code == 404:
                res = await ac.post("/sessions/start", json=sess_req)
            self.assertEqual(res.status_code, 201)
            session_id = res.json()["id"]

            # 4. End Session
            res = await ac.post(f"/api/v1/sessions/{session_id}/end")
            if res.status_code == 404:
                res = await ac.post(f"/sessions/{session_id}/end")
            self.assertEqual(res.status_code, 200)
            end_data = res.json()
            self.assertEqual(end_data["status"], ParkingSessionStatus.COMPLETED.value)
            
            # 5. Process Payment (Mock the success)
            payment_res = await ac.get(f"/api/v1/payments/session/{session_id}")
            if payment_res.status_code == 404:
                payment_res = await ac.get(f"/payments/session/{session_id}")
            payment_id = payment_res.json()["id"]
            
            pay_req = {"simulate_success": True}
            res = await ac.post(f"/api/v1/payments/{payment_id}/process", json=pay_req)
            if res.status_code == 404:
                res = await ac.post(f"/payments/{payment_id}/process", json=pay_req)
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["payment_status"], PaymentStatus.SUCCESS.value)

    @patch("backend.app.services.parking_intelligence_service.ai_service_client")
    async def test_ai_failure_fallback_workflow(self, mock_ai_client):
        # Setup AI mock to FAIL
        mock_ai_client.get_recommendations = AsyncMock(return_value={
            "success": False,
            "error": {"code": "AI_SERVICE_UNAVAILABLE"}
        })
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Discover parking / AI Request
            req = {"latitude": 12.9, "longitude": 77.5, "eta_minutes": 20}
            response = await ac.post("/api/v1/parking/recommend", json=req)
            if response.status_code == 404:
                response = await ac.post("/parking/recommend", json=req)
            # Should still succeed with DB fallback
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue("returned_results" in data)
            
            # The rest of the workflow should still work
            now = datetime.now(timezone.utc)
            start = now + timedelta(minutes=10)
            end = start + timedelta(hours=2)
            res_req = {
                "slot_id": self.slot_id,
                "reservation_start": start.isoformat(),
                "reservation_end": end.isoformat()
            }
            res = await ac.post("/api/v1/reservations", json=res_req)
            if res.status_code == 404:
                res = await ac.post("/reservations", json=res_req)
            self.assertEqual(res.status_code, 201)

    async def test_reservation_concurrency(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            now = datetime.now(timezone.utc)
            start = now + timedelta(minutes=10)
            end = start + timedelta(hours=2)
            res_req = {
                "slot_id": self.slot_id_2,
                "reservation_start": start.isoformat(),
                "reservation_end": end.isoformat()
            }
            
            # We want to fire two reservation requests concurrently for the exact same slot and time
            
            url = "/api/v1/reservations"
            test_resp = await ac.get("/api/v1/facilities")
            if test_resp.status_code == 404:
                url = "/reservations"

            async def make_reservation():
                return await ac.post(url, json=res_req)
                
            results = await asyncio.gather(make_reservation(), make_reservation())
            
            status_codes = [r.status_code for r in results]
            
            # Exactly one should be 201, the other should be 409 Conflict
            self.assertIn(201, status_codes)
            self.assertIn(409, status_codes)
            self.assertEqual(status_codes.count(201), 1)

    async def test_payment_concurrency(self):
        # We need a session and a payment to test concurrency
        async with AsyncSessionLocalTest() as db_session:
            session = ParkingSession(
                user_id=1,
                slot_id=self.slot_id,
                status=ParkingSessionStatus.COMPLETED,
                check_in_time=datetime.now(timezone.utc) - timedelta(hours=2),
                check_out_time=datetime.now(timezone.utc),
                fee_amount=10.00
            )
            db_session.add(session)
            await db_session.commit()
            
            payment = await payment_service.create_payment(db_session, session.id, 1, 10.00)
            payment_id = payment.id

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            url = f"/api/v1/payments/{payment_id}/process"
            
            # Check URL prefix
            test_resp = await ac.get("/api/v1/facilities")
            if test_resp.status_code == 404:
                url = f"/payments/{payment_id}/process"

            pay_req = {"simulate_success": True}

            async def process_payment():
                return await ac.post(url, json=pay_req)
                
            results = await asyncio.gather(process_payment(), process_payment())
            status_codes = [r.status_code for r in results]
            
            # One should succeed (200), the other should fail (400 Bad Request - Payment already processed)
            self.assertIn(200, status_codes)
            self.assertIn(400, status_codes)
            self.assertEqual(status_codes.count(200), 1)
