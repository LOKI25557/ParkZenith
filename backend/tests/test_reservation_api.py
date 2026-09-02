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
from backend.app.models.reservation import ReservationStatus

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

class TestReservationAPI(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        app.dependency_overrides[get_async_session] = override_get_async_session
        app.dependency_overrides[get_admin_user] = override_get_admin_user
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        # Setup basic data (facility, zone, slot)
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

    async def test_create_reservation(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            now = datetime.now(timezone.utc)
            start_time = now + timedelta(hours=1)
            end_time = start_time + timedelta(hours=2)
            
            payload = {
                "slot_id": self.slot_id,
                "reservation_start": start_time.isoformat(),
                "reservation_end": end_time.isoformat()
            }
            
            res = await ac.post("/reservations", json=payload)
            self.assertEqual(res.status_code, 201, res.text)
            data = res.json()
            self.assertEqual(data["slot_id"], self.slot_id)
            self.assertEqual(data["status"], ReservationStatus.CONFIRMED.value)
            
            # Test getting user reservations
            res_list = await ac.get("/reservations")
            self.assertEqual(res_list.status_code, 200)
            self.assertTrue(len(res_list.json()["items"]) >= 1)

    async def test_reservation_overlap(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            now = datetime.now(timezone.utc)
            start_time = now + timedelta(hours=1)
            end_time = start_time + timedelta(hours=2)
            
            payload = {
                "slot_id": self.slot_id,
                "reservation_start": start_time.isoformat(),
                "reservation_end": end_time.isoformat()
            }
            
            # First reservation succeeds
            res1 = await ac.post("/reservations", json=payload)
            self.assertEqual(res1.status_code, 201)
            
            # Second reservation overlapping fails
            payload2 = {
                "slot_id": self.slot_id,
                "reservation_start": (start_time + timedelta(minutes=30)).isoformat(),
                "reservation_end": (end_time + timedelta(minutes=30)).isoformat()
            }
            res2 = await ac.post("/reservations", json=payload2)
            self.assertEqual(res2.status_code, 409)

    async def test_invalid_time_range(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            now = datetime.now(timezone.utc)
            start_time = now + timedelta(hours=2)
            end_time = start_time - timedelta(hours=1) # End before start
            
            payload = {
                "slot_id": self.slot_id,
                "reservation_start": start_time.isoformat(),
                "reservation_end": end_time.isoformat()
            }
            
            res = await ac.post("/reservations", json=payload)
            self.assertEqual(res.status_code, 422) # Pydantic validation error

    async def test_cancel_reservation(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            now = datetime.now(timezone.utc)
            start_time = now + timedelta(hours=1)
            end_time = start_time + timedelta(hours=2)
            
            payload = {
                "slot_id": self.slot_id,
                "reservation_start": start_time.isoformat(),
                "reservation_end": end_time.isoformat()
            }
            
            res = await ac.post("/reservations", json=payload)
            self.assertEqual(res.status_code, 201)
            reservation_id = res.json()["id"]
            
            cancel_res = await ac.delete(f"/reservations/{reservation_id}")
            self.assertEqual(cancel_res.status_code, 200)
            self.assertEqual(cancel_res.json()["status"], ReservationStatus.CANCELLED.value)
