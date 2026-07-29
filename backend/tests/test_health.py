import unittest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app


class TestHealthEndpoint(unittest.IsolatedAsyncioTestCase):

    async def test_health_endpoint(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json().get("message"), "ParkZenith API Running")
