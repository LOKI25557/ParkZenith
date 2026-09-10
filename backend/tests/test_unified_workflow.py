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
from backend.app.models.reservation import Reservation, ReservationStatus

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

async def override_get_async_session():
    async with AsyncSessionLocalTest() as session:
        yield session

async def override_get_current_user():
    return User(id=1, email="user@test.com", is_superuser=False)

async def override_get_admin_user():
    return User(id=2, email="admin@test.com", is_superuser=True)


class TestUnifiedWorkflow(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        app.dependency_overrides[get_async_session] = override_get_async_session
        app.dependency_overrides[get_admin_user] = override_get_admin_user
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        # Setup mock data
        async with AsyncSessionLocalTest() as session:
            facility = ParkingFacility(name="Test Unified", address="Test Address", latitude=12.9, longitude=77.5, is_active=True)
            session.add(facility)
            await session.commit()
            await session.refresh(facility)
            
            zone = ParkingZone(facility_id=facility.id, name="Unified Zone")
            session.add(zone)
            await session.commit()
            await session.refresh(zone)
            
            slots = []
            for i in range(5):
                slot = ParkingSlot(zone_id=zone.id, slot_number=f"U-{i}", status=ParkingSlotStatus.AVAILABLE)
                slots.append(slot)
            
            slots[0].status = ParkingSlotStatus.OCCUPIED
            slots[1].status = ParkingSlotStatus.OCCUPIED
            
            session.add_all(slots)
            await session.commit()
            
            self.facility_id = facility.id
            self.slot_id = slots[0].id

    async def asyncTearDown(self) -> None:
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine_test.dispose()
        app.dependency_overrides.clear()

    @patch("backend.app.services.parking_intelligence_service.ai_service_client")
    async def test_unified_intelligence_with_ai(self, mock_ai_client):
        mock_ai_client.get_intelligence_decision = AsyncMock(return_value={
            "success": True,
            "data": {
                "predicted_occupancy": 85.0,
                "availability_probability": 0.4,
                "predicted_available_slots": 1,
                "recommendation": "LIMITED",
                "reasoning": ["Test reason"],
                "prediction_status": "OK"
            }
        })
        mock_ai_client.get_queue_prediction = AsyncMock(return_value={
            "success": True,
            "data": {"expected_wait_minutes": 15.0}
        })

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get(f"/api/v1/parking/intelligence/{self.facility_id}?eta_minutes=20")
            if response.status_code == 404:
                response = await ac.get(f"/parking/intelligence/{self.facility_id}?eta_minutes=20")
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["facility_id"], self.facility_id)
            self.assertEqual(data["total_slots"], 5)
            self.assertEqual(data["available_slots"], 3)
            self.assertEqual(data["predicted_occupancy_percentage"], 85.0)

    @patch("backend.app.services.parking_intelligence_service.ai_service_client")
    async def test_unified_intelligence_fallback(self, mock_ai_client):
        mock_ai_client.get_intelligence_decision = AsyncMock(return_value={
            "success": False,
            "error": {"code": "AI_SERVICE_UNAVAILABLE"}
        })
        mock_ai_client.get_queue_prediction = AsyncMock(return_value={
            "success": False,
            "error": {"code": "AI_SERVICE_UNAVAILABLE"}
        })

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get(f"/api/v1/parking/intelligence/{self.facility_id}?eta_minutes=20")
            if response.status_code == 404:
                response = await ac.get(f"/parking/intelligence/{self.facility_id}?eta_minutes=20")
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["prediction_status"], "DEGRADED_FALLBACK")
            self.assertEqual(data["predicted_occupancy_percentage"], 40.0)

    @patch("backend.app.services.parking_intelligence_service.ai_service_client")
    async def test_enriched_recommendations(self, mock_ai_client):
        mock_ai_client.get_recommendations = AsyncMock(return_value={
            "success": True,
            "data": {
                "recommendations": [
                    {
                        "rank": 1,
                        "facility_id": str(self.facility_id),
                        "facility_name": "Test Unified",
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
        
        req = {"latitude": 12.9, "longitude": 77.5, "eta_minutes": 20}
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/v1/parking/recommend", json=req)
            if response.status_code == 404:
                response = await ac.post("/parking/recommend", json=req)
                
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["returned_results"], 1)
            self.assertEqual(data["recommendations"][0]["actual_available_slots"], 3)

    async def test_reservation_validation_independent(self):
        now = datetime.now(timezone.utc)
        start = now + timedelta(hours=1)
        end = start + timedelta(hours=2)
        
        # Manually add an overlapping reservation in DB
        async with AsyncSessionLocalTest() as session:
            res = Reservation(
                user_id=1,
                slot_id=self.slot_id,
                reservation_start=start,
                reservation_end=end,
                status=ReservationStatus.CONFIRMED
            )
            session.add(res)
            await session.commit()
            
        req = {
            "slot_id": self.slot_id,
            "reservation_start": start.isoformat(),
            "reservation_end": end.isoformat()
        }
        
        # Expect failure due to strict reservation overlap protection
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True) as ac:
            response = await ac.post("/api/v1/reservations", json=req, headers={"Authorization": "Bearer test"})
            if response.status_code == 404:
                response = await ac.post("/reservations", json=req, headers={"Authorization": "Bearer test"})
            
            self.assertEqual(response.status_code, 409)
