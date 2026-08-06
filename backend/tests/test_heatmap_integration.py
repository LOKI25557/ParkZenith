"""
Integration tests for the backend Heatmap API endpoints and AI Service Client integration.
"""

import unittest
from unittest.mock import patch
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.services.ai_service_client import AIServiceClient, ai_service_client


class TestHeatmapIntegration(unittest.IsolatedAsyncioTestCase):
    """
    Test suite verifying backend heatmap API endpoints, schema mappings, and error translation.
    """

    def setUp(self) -> None:
        self.mock_point = {
            "latitude": 12.9716,
            "longitude": 77.5946,
            "intensity": 65.0,
            "zone_id": "ZONE-A",
            "facility_id": "1",
        }
        self.mock_zone = {
            "zone_id": "ZONE-A",
            "density_score": 65.0,
            "occupancy_percentage": 65.0,
            "occupied_slots": 32,
            "total_slots": 50,
            "intensity": 65.0,
        }
        self.mock_congestion = {
            "congestion_index": 62.0,
            "congestion_level": "MODERATE",
            "capacity_utilization": 60.0,
            "zone_utilization": 65.0,
        }
        self.mock_facility = {
            "facility_id": "1",
            "facility_name": "Downtown Central Parking",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "overall_density": 60.0,
            "overall_congestion_score": self.mock_congestion,
            "points": [self.mock_point],
            "zones": [self.mock_zone],
        }

    async def test_backend_heatmap_live(self) -> None:
        """Test GET /heatmap and GET /heatmap/live success states."""
        mock_response = {
            "success": True,
            "data": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "facilities": [self.mock_facility]
            }
        }
        
        with patch.object(AIServiceClient, "_make_request", return_value=mock_response) as mock_req:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                # Test overall endpoint
                resp = await ac.get("/heatmap")
                self.assertEqual(resp.status_code, 200)
                data = resp.json()
                self.assertIn("timestamp", data)
                self.assertEqual(data["facilities"][0]["facility_id"], "1")
                
                # Test live endpoint
                resp_live = await ac.get("/heatmap/live")
                self.assertEqual(resp_live.status_code, 200)
                
            mock_req.assert_any_call("GET", "/heatmap")
            mock_req.assert_any_call("GET", "/heatmap/live")

    async def test_backend_heatmap_history(self) -> None:
        """Test GET /heatmap/history."""
        mock_response = {
            "success": True,
            "data": {
                "start_time": datetime.now(timezone.utc).isoformat(),
                "end_time": datetime.now(timezone.utc).isoformat(),
                "interval": "daily",
                "facilities": [self.mock_facility]
            }
        }
        
        with patch.object(AIServiceClient, "_make_request", return_value=mock_response) as mock_req:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.get("/heatmap/history?interval=daily&facility_id=1")
                self.assertEqual(resp.status_code, 200)
                data = resp.json()
                self.assertEqual(data["interval"], "daily")
                
            mock_req.assert_called_once_with(
                "GET", 
                "/heatmap/history", 
                params={"interval": "daily", "facility_id": "1"}
            )

    async def test_backend_heatmap_zones(self) -> None:
        """Test GET /heatmap/zones."""
        mock_response = {
            "success": True,
            "data": {
                "most_congested_zones": ["ZONE-A"],
                "least_occupied_zones": ["ZONE-B"],
                "average_density": 55.0,
                "peak_congestion_periods": [{"period": "14:00 - 15:00", "density": 85.0}],
                "heatmap_summaries": {"general": "Moderate traffic."},
                "zones": [self.mock_zone]
            }
        }
        
        with patch.object(AIServiceClient, "_make_request", return_value=mock_response) as mock_req:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.get("/heatmap/zones?facility_id=1")
                self.assertEqual(resp.status_code, 200)
                data = resp.json()
                self.assertEqual(data["most_congested_zones"][0], "ZONE-A")
                
            mock_req.assert_called_once_with("GET", "/heatmap/zones", params={"facility_id": "1"})

    async def test_backend_heatmap_facility(self) -> None:
        """Test GET /heatmap/facility/{facility_id}."""
        mock_response = {
            "success": True,
            "data": self.mock_facility
        }
        
        with patch.object(AIServiceClient, "_make_request", return_value=mock_response) as mock_req:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.get("/heatmap/facility/1")
                self.assertEqual(resp.status_code, 200)
                data = resp.json()
                self.assertEqual(data["facility_id"], "1")
                
            mock_req.assert_called_once_with("GET", "/heatmap/facility/1")

    async def test_error_translation_offline(self) -> None:
        """Test that client connection or unavailable errors map to 503."""
        mock_error = {
            "success": False,
            "error": {
                "code": "AI_SERVICE_UNAVAILABLE",
                "message": "AI Service unreachable",
                "status_code": 503
            }
        }
        with patch.object(AIServiceClient, "_make_request", return_value=mock_error):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.get("/heatmap/live")
                self.assertEqual(resp.status_code, 503)
                self.assertIn("AI Service unreachable", resp.json()["detail"])

    async def test_error_translation_not_found(self) -> None:
        """Test that missing facility error maps to 404."""
        mock_error = {
            "success": False,
            "error": {
                "code": "MISSING_FACILITY",
                "message": "Facility not found",
                "status_code": 404
            }
        }
        with patch.object(AIServiceClient, "_make_request", return_value=mock_error):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.get("/heatmap/facility/999")
                self.assertEqual(resp.status_code, 404)
