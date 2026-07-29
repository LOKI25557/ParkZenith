import unittest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from backend.app.main import app
from backend.app.database.session import get_async_session
from backend.app.models.base import Base

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


app.dependency_overrides[get_async_session] = override_get_async_session


class TestAuthFlow(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self) -> None:
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine_test.dispose()

    async def test_auth_full_flow(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Register a user
            reg_payload = {
                "email": "test@example.com",
                "full_name": "Test User",
                "phone": "+1234567890",
                "vehicle_number": "KA-01-AB-1234",
                "password": "strongpassword123",
            }
            resp = await ac.post("/auth/register", json=reg_payload)
            self.assertEqual(resp.status_code, 201)
            data = resp.json()
            self.assertEqual(data.get("email"), "test@example.com")
            self.assertEqual(data.get("full_name"), "Test User")
            self.assertNotIn("password", data)
            self.assertNotIn("password_hash", data)

            # 2. Check duplicate registration (must return 409 Conflict)
            resp_dup = await ac.post("/auth/register", json=reg_payload)
            self.assertEqual(resp_dup.status_code, 409)

            # 3. Validation error check (password too short)
            bad_payload = reg_payload.copy()
            bad_payload["email"] = "other@example.com"
            bad_payload["password"] = "short"
            resp_short = await ac.post("/auth/register", json=bad_payload)
            self.assertEqual(resp_short.status_code, 422)

            # 4. Login with incorrect password (must return 401)
            login_payload_bad = {
                "email": "test@example.com",
                "password": "wrongpassword",
            }
            resp_login_bad = await ac.post("/auth/login", json=login_payload_bad)
            self.assertEqual(resp_login_bad.status_code, 401)

            # 5. Login with correct credentials (must return token)
            login_payload = {
                "email": "test@example.com",
                "password": "strongpassword123",
            }
            resp_login = await ac.post("/auth/login", json=login_payload)
            self.assertEqual(resp_login.status_code, 200)
            token_data = resp_login.json()
            self.assertIn("access_token", token_data)
            self.assertEqual(token_data.get("token_type"), "bearer")
            
            token = token_data.get("access_token")
            headers = {"Authorization": f"Bearer {token}"}

            # 6. Retrieve profile of currently logged in user (GET /auth/me)
            resp_me = await ac.get("/auth/me", headers=headers)
            self.assertEqual(resp_me.status_code, 200)
            me_data = resp_me.json()
            self.assertEqual(me_data.get("email"), "test@example.com")
            self.assertEqual(me_data.get("phone"), "+1234567890")

            # 7. Access profile route with missing token (must return 401)
            resp_me_no_token = await ac.get("/auth/me")
            self.assertEqual(resp_me_no_token.status_code, 401)

            # 8. Access profile route with invalid token (must return 401)
            resp_me_bad_token = await ac.get("/auth/me", headers={"Authorization": "Bearer invalidtoken"})
            self.assertEqual(resp_me_bad_token.status_code, 401)

            # 9. Update profile details (PUT /users/profile)
            update_payload = {
                "full_name": "Updated User Name",
                "phone": "+9876543210",
                "vehicle_number": "KA-05-XY-9999",
            }
            resp_update = await ac.put("/users/profile", json=update_payload, headers=headers)
            self.assertEqual(resp_update.status_code, 200)
            update_data = resp_update.json()
            self.assertEqual(update_data.get("full_name"), "Updated User Name")
            self.assertEqual(update_data.get("phone"), "+9876543210")
            self.assertEqual(update_data.get("vehicle_number"), "KA-05-XY-9999")
            self.assertEqual(update_data.get("email"), "test@example.com")  # Email should remain unchanged
