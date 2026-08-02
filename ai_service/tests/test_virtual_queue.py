import asyncio
import unittest
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from ai_service.main import app
from ai_service.database.session import get_db_session
from ai_service.database.base import Base
from ai_service.models.occupancy import OccupancyHistory
from ai_service.services.queue_service import QueueService
from ai_service.api.deps import get_queue_service

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


class TestVirtualQueue(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        app.dependency_overrides[get_db_session] = override_get_db_session

        # Insert a valid facility to allow virtual queue operations
        async with AsyncSessionLocalTest() as session:
            occ = OccupancyHistory(
                facility_id="FAC-V",
                zone_id="ZONE-V",
                total_slots=100,
                occupied_slots=50,
                available_slots=50,
                occupancy_percentage=50.0,
                collected_at=datetime.now(timezone.utc)
            )
            session.add(occ)
            await session.commit()

        # Retrieve singleton queue service and clear virtual queue manager
        self.queue_service = get_queue_service()
        self.queue_service.virtual_queue_manager.clear_all()

    async def asyncTearDown(self) -> None:
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine_test.dispose()
        app.dependency_overrides.clear()

    async def test_virtual_queue_basic_operations(self) -> None:
        """Test enqueue, position lookup, cancel, and dequeue flow."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Enqueue User 1
            resp = await client.post("/queue/FAC-V/enqueue", json={"user_id": "USER-1"})
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["position"], 1)
            self.assertEqual(data["user_id"], "USER-1")

            # 2. Enqueue User 2
            resp = await client.post("/queue/FAC-V/enqueue", json={"user_id": "USER-2"})
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json()["position"], 2)

            # 3. Position Lookup for User 2
            resp = await client.get("/queue/FAC-V/position?user_id=USER-2")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json()["position"], 2)

            # 4. Dequeue front (pops USER-1)
            resp = await client.post("/queue/FAC-V/dequeue", json={})
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(resp.json()["success"])
            self.assertEqual(resp.json()["user_id"], "USER-1")

            # 5. Position Lookup for USER-2 should now be 1
            resp = await client.get("/queue/FAC-V/position?user_id=USER-2")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json()["position"], 1)

            # 6. Dequeue USER-2 specifically
            resp = await client.post("/queue/FAC-V/dequeue", json={"user_id": "USER-2"})
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(resp.json()["success"])
            self.assertEqual(resp.json()["user_id"], "USER-2")

    async def test_virtual_queue_duplicate_handling(self) -> None:
        """Test joining a queue twice returns same position instead of appending."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Enqueue User A
            resp = await client.post("/queue/FAC-V/enqueue", json={"user_id": "USER-A"})
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json()["position"], 1)

            # Enqueue User B
            resp = await client.post("/queue/FAC-V/enqueue", json={"user_id": "USER-B"})
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json()["position"], 2)

            # Enqueue User A again (duplicate check)
            resp2 = await client.post("/queue/FAC-V/enqueue", json={"user_id": "USER-A"})
            self.assertEqual(resp2.status_code, 200)
            self.assertEqual(resp2.json()["position"], 1)  # remains at position 1

            # Queue length should still be 2, not 3
            resp_pos = await client.get("/queue/FAC-V/position?user_id=USER-B")
            self.assertEqual(resp_pos.json()["position"], 2)

    async def test_virtual_queue_cancel(self) -> None:
        """Test cancelling a queue spot."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/queue/FAC-V/enqueue", json={"user_id": "USER-X"})
            await client.post("/queue/FAC-V/enqueue", json={"user_id": "USER-Y"})

            # Cancel USER-X
            resp = await client.post("/queue/FAC-V/cancel", json={"user_id": "USER-X"})
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(resp.json()["success"])
            self.assertEqual(resp.json()["user_id"], "USER-X")

            # USER-X lookup should be None
            resp_lookup = await client.get("/queue/FAC-V/position?user_id=USER-X")
            self.assertEqual(resp_lookup.status_code, 200)
            self.assertIsNone(resp_lookup.json()["position"])

            # USER-Y position should decrease to 1
            resp_lookup_y = await client.get("/queue/FAC-V/position?user_id=USER-Y")
            self.assertEqual(resp_lookup_y.json()["position"], 1)

    async def test_virtual_queue_invalid_facility(self) -> None:
        """Test queue operations reject invalid facility IDs."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/queue/INVALID-FAC/enqueue", json={"user_id": "USER-1"})
            self.assertEqual(resp.status_code, 404)
            self.assertIn("has no historical records", resp.json()["error"]["message"])

    async def test_virtual_queue_empty_dequeue(self) -> None:
        """Test dequeueing from an empty queue returns success=False."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/queue/FAC-V/dequeue", json={})
            self.assertEqual(resp.status_code, 200)
            self.assertFalse(resp.json()["success"])
            self.assertIsNone(resp.json()["user_id"])

    async def test_virtual_queue_concurrency_race(self) -> None:
        """Concurrently enqueue multiple users to test safety against race conditions."""
        # Use direct service calls in parallel tasks
        async with AsyncSessionLocalTest() as session:
            tasks = [
                self.queue_service.enqueue_user(session, "FAC-V", f"USER-CONC-{i}")
                for i in range(50)
            ]
            positions = await asyncio.gather(*tasks)

            # Verify all positions are unique integers from 1 to 50
            self.assertEqual(len(positions), 50)
            self.assertEqual(len(set(positions)), 50)
            self.assertEqual(min(positions), 1)
            self.assertEqual(max(positions), 50)
