import unittest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
import asyncio

from backend.app.main import app
from backend.app.database.session import get_async_session
from backend.app.models.base import Base
from backend.app.core.dependencies import get_admin_user, get_current_user
from backend.app.models.user import User
from backend.app.models.parking_slot import ParkingSlotStatus

# Setup an in-memory SQLite database specifically for test isolated runs
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


class TestParkingAPI(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        app.dependency_overrides[get_async_session] = override_get_async_session
        app.dependency_overrides[get_admin_user] = override_get_admin_user
        app.dependency_overrides[get_current_user] = override_get_current_user

    async def asyncTearDown(self) -> None:
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine_test.dispose()
        app.dependency_overrides.clear()

    async def test_facility_crud(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # Create
            payload = {
                "name": "Central Parking",
                "address": "123 Main St",
                "total_slots": 100
            }
            res = await ac.post("/api/v1/facilities", json=payload)
            if res.status_code == 404:  # Adjusting for prefix if needed
                res = await ac.post("/facilities", json=payload)
            self.assertEqual(res.status_code, 201)
            facility_id = res.json()["id"]

            # Get
            res = await ac.get(f"/facilities/{facility_id}")
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["name"], "Central Parking")

            # List
            res = await ac.get("/facilities")
            self.assertEqual(res.status_code, 200)
            self.assertTrue(len(res.json()) >= 1)

            # Update
            res = await ac.patch(f"/facilities/{facility_id}", json={"name": "Updated Parking"})
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["name"], "Updated Parking")

            # Delete
            res = await ac.delete(f"/facilities/{facility_id}")
            self.assertEqual(res.status_code, 204)

            # Nonexistent
            res = await ac.get(f"/facilities/{facility_id}")
            self.assertEqual(res.status_code, 404)

    async def test_zone_crud(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            facility_res = await ac.post("/facilities", json={"name": "F1", "address": "A1"})
            facility_id = facility_res.json()["id"]

            # Create Zone
            res = await ac.post(f"/facilities/{facility_id}/zones", json={"name": "Zone A"})
            self.assertEqual(res.status_code, 201)
            zone_id = res.json()["id"]

            # Get Zone
            res = await ac.get(f"/zones/{zone_id}")
            self.assertEqual(res.status_code, 200)

            # List Zones
            res = await ac.get(f"/facilities/{facility_id}/zones")
            self.assertEqual(res.status_code, 200)
            self.assertTrue(len(res.json()) >= 1)

            # Update Zone
            res = await ac.patch(f"/zones/{zone_id}", json={"name": "Zone B"})
            self.assertEqual(res.status_code, 200)

            # Invalid facility zone create
            res = await ac.post(f"/facilities/999/zones", json={"name": "Zone C"})
            self.assertEqual(res.status_code, 404)

            # Delete Zone
            res = await ac.delete(f"/zones/{zone_id}")
            self.assertEqual(res.status_code, 204)

    async def test_slot_crud(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            facility_res = await ac.post("/facilities", json={"name": "F1", "address": "A1"})
            facility_id = facility_res.json()["id"]
            zone_res = await ac.post(f"/facilities/{facility_id}/zones", json={"name": "Z1"})
            zone_id = zone_res.json()["id"]

            # Create Slot
            res = await ac.post(f"/zones/{zone_id}/slots", json={"slot_number": "A1"})
            self.assertEqual(res.status_code, 201)
            slot_id = res.json()["id"]

            # Get Slot
            res = await ac.get(f"/slots/{slot_id}")
            self.assertEqual(res.status_code, 200)

            # List Slots
            res = await ac.get(f"/zones/{zone_id}/slots")
            self.assertEqual(res.status_code, 200)

            # Update Slot
            res = await ac.patch(f"/slots/{slot_id}", json={"slot_number": "A2"})
            self.assertEqual(res.status_code, 200)

            # Invalid zone slot create
            res = await ac.post(f"/zones/999/slots", json={"slot_number": "A3"})
            self.assertEqual(res.status_code, 404)

            # Delete Slot
            res = await ac.delete(f"/slots/{slot_id}")
            self.assertEqual(res.status_code, 204)

    async def test_slot_status(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            facility_res = await ac.post("/facilities", json={"name": "F1", "address": "A1"})
            zone_res = await ac.post(f"/facilities/{facility_res.json()['id']}/zones", json={"name": "Z1"})
            slot_res = await ac.post(f"/zones/{zone_res.json()['id']}/slots", json={"slot_number": "S1"})
            slot_id = slot_res.json()["id"]

            for status in [ParkingSlotStatus.OCCUPIED.value, ParkingSlotStatus.RESERVED.value, ParkingSlotStatus.AVAILABLE.value]:
                res = await ac.patch(f"/slots/{slot_id}/status", json={"status": status})
                self.assertEqual(res.status_code, 200)
                self.assertEqual(res.json()["status"], status)

            res = await ac.patch(f"/slots/{slot_id}/status", json={"status": "INVALID_STATUS"})
            self.assertEqual(res.status_code, 422)

    async def test_availability(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            f_res = await ac.post("/facilities", json={"name": "F1", "address": "A1"})
            f_id = f_res.json()["id"]
            z_res = await ac.post(f"/facilities/{f_id}/zones", json={"name": "Z1"})
            z_id = z_res.json()["id"]

            s1 = await ac.post(f"/zones/{z_id}/slots", json={"slot_number": "S1"})
            s2 = await ac.post(f"/zones/{z_id}/slots", json={"slot_number": "S2"})
            await ac.patch(f"/slots/{s1.json()['id']}/status", json={"status": "occupied"})

            f_avail = await ac.get(f"/facilities/{f_id}/availability")
            self.assertEqual(f_avail.status_code, 200)
            data = f_avail.json()
            self.assertEqual(data["total_slots"], 2)
            self.assertEqual(data["available"], 1)
            self.assertEqual(data["occupied"], 1)

            z_avail = await ac.get(f"/zones/{z_id}/availability")
            self.assertEqual(z_avail.status_code, 200)
            data = z_avail.json()
            self.assertEqual(data["total_slots"], 2)

    async def test_authorization(self):
        from fastapi import HTTPException
        async def override_get_admin_user_fail():
            raise HTTPException(status_code=403, detail="Not enough privileges")
            
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            app.dependency_overrides[get_admin_user] = override_get_admin_user_fail

            res = await ac.post("/facilities", json={"name": "Fail", "address": "Fail"})
            self.assertEqual(res.status_code, 403)
            
            # Restore override
            app.dependency_overrides[get_admin_user] = override_get_admin_user
