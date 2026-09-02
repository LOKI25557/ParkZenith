import unittest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
import asyncio
from datetime import datetime, timedelta, timezone

from backend.app.main import app
from backend.app.database.session import get_async_session
from backend.app.models.base import Base
from backend.app.core.dependencies import get_admin_user, get_current_user
from backend.app.models.user import User
from backend.app.models.session import ParkingSessionStatus
from backend.app.models.parking_slot import ParkingSlotStatus

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

class TestSessionAPI(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        app.dependency_overrides[get_async_session] = override_get_async_session
        app.dependency_overrides[get_admin_user] = override_get_admin_user
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            f_res = await ac.post("/facilities", json={"name": "F1", "address": "A1"})
            self.facility_id = f_res.json()["id"]
            
            z_res = await ac.post(f"/facilities/{self.facility_id}/zones", json={"name": "Z1"})
            self.zone_id = z_res.json()["id"]
            
            s_res = await ac.post(f"/zones/{self.zone_id}/slots", json={"slot_number": "S1"})
            self.slot_id = s_res.json()["id"]

    async def asyncTearDown(self) -> None:
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine_test.dispose()
        app.dependency_overrides.clear()

    async def test_start_session_without_reservation(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "slot_id": self.slot_id
            }
            
            res = await ac.post("/sessions/start", json=payload)
            if res.status_code != 201:
                print(res.json())
            self.assertEqual(res.status_code, 201)
            data = res.json()
            self.assertEqual(data["slot_id"], self.slot_id)
            self.assertEqual(data["status"], ParkingSessionStatus.ACTIVE.value)
            
            # Check slot status updated
            slot_res = await ac.get(f"/slots/{self.slot_id}")
            self.assertEqual(slot_res.json()["status"], ParkingSlotStatus.OCCUPIED.value)

    async def test_start_session_with_reservation(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            now = datetime.now(timezone.utc)
            start_time = now - timedelta(minutes=5)
            end_time = now + timedelta(hours=1)
            
            res_payload = {
                "slot_id": self.slot_id,
                "reservation_start": start_time.isoformat(),
                "reservation_end": end_time.isoformat()
            }
            res = await ac.post("/reservations", json=res_payload)
            self.assertEqual(res.status_code, 201, res.text)
            reservation_id = res.json()["id"]
            
            # Start session
            sess_payload = {
                "slot_id": self.slot_id,
                "reservation_id": reservation_id
            }
            sess_res = await ac.post("/sessions/start", json=sess_payload)
            self.assertEqual(sess_res.status_code, 201)

    async def test_end_session(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "slot_id": self.slot_id
            }
            
            res = await ac.post("/sessions/start", json=payload)
            self.assertEqual(res.status_code, 201)
            session_id = res.json()["id"]
            
            end_res = await ac.post(f"/sessions/{session_id}/end")
            self.assertEqual(end_res.status_code, 200)
            data = end_res.json()
            self.assertEqual(data["status"], ParkingSessionStatus.COMPLETED.value)
            self.assertIsNotNone(data["check_out_time"])
            self.assertIsNotNone(data["duration_minutes"])
            
            # Check slot status updated back to available
            slot_res = await ac.get(f"/slots/{self.slot_id}")
            self.assertEqual(slot_res.json()["status"], ParkingSlotStatus.AVAILABLE.value)

    async def test_active_session(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "slot_id": self.slot_id
            }
            await ac.post("/sessions/start", json=payload)
            
            res = await ac.get("/sessions/active")
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["slot_id"], self.slot_id)
