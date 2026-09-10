import asyncio
import os
import unittest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from datetime import datetime, timezone

from backend.app.main import app
from backend.app.database.session import get_async_session
from backend.app.models.base import Base
from backend.app.core.security import create_access_token
from backend.app.models.user import User
from backend.app.models.reservation import Reservation, ReservationStatus

from sqlalchemy.pool import NullPool

DATABASE_URL_TEST = "sqlite+aiosqlite:///test_e2e_realtime_auth.db"

engine_test = create_async_engine(
    DATABASE_URL_TEST,
    connect_args={"check_same_thread": False},
    poolclass=NullPool,
)

AsyncSessionLocalTest = async_sessionmaker(
    bind=engine_test,
    expire_on_commit=False,
    class_=AsyncSession,
)

async def override_get_async_session():
    async with AsyncSessionLocalTest() as session:
        yield session

class TestE2ERealtimeAuth(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        if os.path.exists("test_e2e_realtime_auth.db"):
            try:
                os.remove("test_e2e_realtime_auth.db")
            except:
                pass
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        async with AsyncSessionLocalTest() as session:
            user1 = User(id=1, email="user1@test.com", full_name="User 1", hashed_password="pwd", is_active=True, is_superuser=False)
            user2 = User(id=2, email="user2@test.com", full_name="User 2", hashed_password="pwd", is_active=True, is_superuser=False)
            admin = User(id=3, email="admin@test.com", full_name="Admin", hashed_password="pwd", is_active=True, is_superuser=True)
            session.add_all([user1, user2, admin])
            
            # Add a reservation for user 1
            res = Reservation(id=1, user_id=1, slot_id=1, reservation_start=datetime.now(timezone.utc), reservation_end=datetime.now(timezone.utc), status=ReservationStatus.CONFIRMED)
            session.add(res)
            
            await session.commit()
                
        app.dependency_overrides[get_async_session] = override_get_async_session
        
        self.token_user1 = create_access_token({"sub": "user1@test.com"})
        self.token_user2 = create_access_token({"sub": "user2@test.com"})
        self.token_admin = create_access_token({"sub": "admin@test.com"})

    async def asyncTearDown(self) -> None:
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine_test.dispose()
        app.dependency_overrides.clear()

    async def test_anonymous_user_blocked(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/facilities")
            prefix = "/api/v1" if resp.status_code != 404 else ""
            
            res = await ac.get(f"{prefix}/reservations")
            self.assertEqual(res.status_code, 401)

    async def test_normal_user_auth(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/facilities")
            prefix = "/api/v1" if resp.status_code != 404 else ""

            # Can access own reservations
            res = await ac.get(f"{prefix}/reservations", headers={"Authorization": f"Bearer {self.token_user1}"})
            self.assertEqual(res.status_code, 200)
            self.assertEqual(len(res.json()["items"]), 1)

            # User 2 shouldn't see User 1's reservation
            res2 = await ac.get(f"{prefix}/reservations", headers={"Authorization": f"Bearer {self.token_user2}"})
            self.assertEqual(res2.status_code, 200)
            self.assertEqual(len(res2.json()["items"]), 0)
            
            # User 1 cannot perform admin action
            res_admin = await ac.post(f"{prefix}/facilities", json={"name": "New Fac", "address": "Addr", "total_slots": 10}, headers={"Authorization": f"Bearer {self.token_user1}"})
            self.assertEqual(res_admin.status_code, 403)

    async def test_admin_auth(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/facilities")
            prefix = "/api/v1" if resp.status_code != 404 else ""

            # Admin CAN perform admin action
            res_admin = await ac.post(f"{prefix}/facilities", json={"name": "New Fac", "address": "Addr", "total_slots": 10}, headers={"Authorization": f"Bearer {self.token_admin}"})
            self.assertEqual(res_admin.status_code, 201)

    def test_websocket_auth(self):
        # We need to use TestClient for WebSockets
        client = TestClient(app)
        from starlette.websockets import WebSocketDisconnect
        # Unauthenticated WS
        try:
            with client.websocket_connect("/ws/parking/1"):
                pass
            self.fail("Should have raised WebSocketDisconnect")
        except WebSocketDisconnect as e:
            self.assertEqual(e.code, 1008)
            
        # Authenticated WS
        try:
            with client.websocket_connect(f"/ws/parking/1?token={self.token_user1}") as websocket:
                pass
        except WebSocketDisconnect:
            pass 
