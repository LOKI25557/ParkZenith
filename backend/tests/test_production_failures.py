import unittest
from unittest.mock import patch, MagicMock
import httpx
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core.metrics import metrics
from backend.app.services.ai_service_client import ai_service_client


class TestProductionFailures(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        from backend.app.core.cache import cache
        cache.clear()
        metrics.reset()

    async def test_database_connection_failure(self):
        """Simulate a database connection error during a request."""
        # Mock database session to raise a connection/operational error
        # Also mock AI service health probe to return healthy, so it asserts degraded state
        original_get = httpx.AsyncClient.get

        async def mock_get(client_self, url, *args, **kwargs):
            if "localhost:8001" in str(url) or "ai-service" in str(url):
                return httpx.Response(status_code=200, json={"status": "READY"})
            return await original_get(client_self, url, *args, **kwargs)

        with patch("backend.app.main.AsyncSessionLocal") as mock_db, \
             patch("httpx.AsyncClient.get", side_effect=mock_get, autospec=True):
             
            mock_db.side_effect = Exception("OperationalError: database connection lost")
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                # Ready check endpoint queries database and registers database state
                resp = await ac.get("/ready")
                self.assertEqual(resp.status_code, 200)
                data = resp.json()
                self.assertEqual(data["status"], "DEGRADED")
                self.assertEqual(data["database"], "DISCONNECTED")

    async def test_ai_service_timeout_triggers_fallback_and_records_metrics(self):
        """Simulate httpx connection timeout and check fallback mechanism + observability metrics."""
        original_request = httpx.AsyncClient.request

        async def mock_request(client_self, method, url, *args, **kwargs):
            if "localhost:8001" in str(url) or "ai-service" in str(url):
                raise httpx.TimeoutException("Connection timed out")
            return await original_request(client_self, method, url, *args, **kwargs)

        with patch("httpx.AsyncClient.request", side_effect=mock_request, autospec=True), \
             patch.object(ai_service_client, "retry_count", 0):
             
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.get("/prediction/occupancy/1?horizon_minutes=15")
                self.assertEqual(resp.status_code, 200)
                data = resp.json()
                
                # Assert fallback data structure
                self.assertEqual(data["prediction_status"], "DEGRADED_FALLBACK")
                self.assertEqual(data["facility_id"], 1)
                
                # Check that observability registered the failure
                summary = metrics.get_metrics_summary()
                total_requests = sum(summary["request_counts"].values())
                self.assertEqual(total_requests, 1)
                self.assertEqual(summary["prediction_failures"], 1)
                self.assertEqual(summary["ai_service_failures"], 1)

    async def test_ai_service_500_response_triggers_fallback(self):
        """Simulate AI Service returning a internal 500 error code with a fallback-triggering error code."""
        original_request = httpx.AsyncClient.request

        async def mock_request(client_self, method, url, *args, **kwargs):
            if "localhost:8001" in str(url) or "ai-service" in str(url):
                return httpx.Response(status_code=500, json={
                    "error": {
                        "code": "MODEL_UNAVAILABLE",
                        "message": "AI service model is currently not loaded or trained"
                    }
                })
            return await original_request(client_self, method, url, *args, **kwargs)
        
        with patch("httpx.AsyncClient.request", side_effect=mock_request, autospec=True):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.get("/prediction/availability/1?eta_minutes=20")
                self.assertEqual(resp.status_code, 200)
                data = resp.json()
                
                self.assertEqual(data["prediction_status"], "DEGRADED_FALLBACK")
                self.assertEqual(data["facility_id"], "1")

    async def test_ai_service_invalid_json_response_triggers_fallback(self):
        """Simulate AI Service returning malformed/invalid JSON, which should be caught and fallback triggered."""
        original_request = httpx.AsyncClient.request

        async def mock_request(client_self, method, url, *args, **kwargs):
            if "localhost:8001" in str(url) or "ai-service" in str(url):
                # Return non-JSON response with HTTP 200 status code
                return httpx.Response(status_code=200, content=b"Invalid JSON data from AI service")
            return await original_request(client_self, method, url, *args, **kwargs)
        
        with patch("httpx.AsyncClient.request", side_effect=mock_request, autospec=True):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.get("/prediction/occupancy/1?horizon_minutes=15")
                self.assertEqual(resp.status_code, 200)
                data = resp.json()
                
                self.assertEqual(data["prediction_status"], "DEGRADED_FALLBACK")
                self.assertEqual(data["facility_id"], 1)

