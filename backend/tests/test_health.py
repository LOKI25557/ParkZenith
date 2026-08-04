import unittest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app


class TestHealthEndpoint(unittest.IsolatedAsyncioTestCase):

    async def test_health_endpoint(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json().get("message"), "ParkZenith API Running")

    async def test_health_live_endpoint(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/health")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json().get("status"), "HEALTHY")

    async def test_ready_endpoint_success(self):
        from unittest.mock import patch, MagicMock
        # Mock database session execution and httpx call to AI Service
        with patch("backend.app.database.session.AsyncSessionLocal") as mock_session_local:
            mock_session = MagicMock()
            async def mock_execute(*args, **kwargs):
                return None
            mock_session.execute = mock_execute
            async def mock_close():
                return None
            mock_session.close = mock_close
            async def mock_enter(*args, **kwargs):
                return mock_session
            async def mock_exit(*args, **kwargs):
                return None
            mock_session_local.return_value.__aenter__ = mock_enter
            mock_session_local.return_value.__aexit__ = mock_exit

            with patch("backend.app.main.httpx.AsyncClient") as mock_client_class:
                mock_client = MagicMock()
                mock_response = MagicMock()
                mock_response.status_code = 200
                async def mock_get_call(*args, **kwargs):
                    return mock_response
                mock_client.get = mock_get_call
                async def mock_client_enter(*args, **kwargs):
                    return mock_client
                async def mock_client_exit(*args, **kwargs):
                    return None
                mock_client_class.return_value.__aenter__ = mock_client_enter
                mock_client_class.return_value.__aexit__ = mock_client_exit

                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                    resp = await ac.get("/ready")
                    self.assertEqual(resp.status_code, 200)
                    self.assertEqual(resp.json().get("status"), "READY")
                    self.assertEqual(resp.json().get("database"), "CONNECTED")
                    self.assertEqual(resp.json().get("ai_service"), "CONNECTED")
