"""
Verification tests for the consolidated AI Dashboard prediction API in backend.
"""

import unittest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.services.ai_service_client import AIServiceClient, ai_service_client


class TestAIDashboardIntegration(unittest.IsolatedAsyncioTestCase):
    """
    Test suite verifying backend-side AI Dashboard integration.
    """

    def setUp(self):
        from backend.app.core.cache import cache
        cache.clear()

    def tearDown(self):
        from backend.app.core.cache import cache
        cache.clear()

    async def test_backend_dashboard_endpoint_success(self):
        """Test successful dashboard retrieval from AI Service."""
        mock_response = {
            "success": True,
            "data": {
                "occupancy": {
                    "facility_id": "1",
                    "current_occupancy": 75.0,
                    "total_capacity": 100,
                    "available_spaces": 25,
                    "occupied_spaces": 75,
                    "reserved_spaces": 5,
                    "utilization_percentage": 75.0,
                    "historical_occupancy": [],
                    "peak_occupancy": 85.0,
                    "peak_hours": [17],
                    "occupancy_trends": {}
                },
                "forecast": {
                    "forecast_30m": 80.0,
                    "forecast_60m": 85.0,
                    "forecast_horizon": [],
                    "confidence": 0.95,
                    "expected_demand": 80.0,
                    "expected_occupancy": 80.0,
                    "peak_demand_window": "17:00-19:00",
                    "event_adjusted_forecast": 85.0
                },
                "availability": {
                    "arrival_availability_probability": 85.0,
                    "eta_minutes": 20,
                    "expected_occupancy_at_arrival": 80.0,
                    "available_capacity": 20,
                    "confidence": 0.95,
                    "risk_level": "LOW"
                },
                "recommendations": {
                    "recommended_facilities": [],
                    "summary_insights": ["Facility 1 is currently the best option."]
                },
                "queue": {
                    "current_queue_estimate": 2,
                    "predicted_waiting_time": 4.5,
                    "congestion_level": "MODERATE",
                    "queue_growth": 0.1,
                    "peak_queue_period": None,
                    "event_adjusted_queue_prediction": 4.5
                },
                "heatmap": {
                    "zone_congestion": [],
                    "most_congested_zones": [],
                    "least_congested_zones": [],
                    "peak_congestion_period": None,
                    "historical_comparison": {}
                },
                "events": {
                    "active_events": [],
                    "upcoming_events": [],
                    "event_impact": {},
                    "expected_demand_increase": 0.0,
                    "affected_facilities": [],
                    "congestion_risk": "LOW",
                    "event_adjusted_occupancy": 75.0,
                    "event_adjusted_queue_estimates": 4.5
                },
                "performance": {
                    "prediction_accuracy": 94.8,
                    "error_metrics": {},
                    "confidence": 0.95,
                    "forecast_performance": {},
                    "availability_prediction_performance": {},
                    "recommendation_performance": {},
                    "queue_prediction_performance": {}
                },
                "insights": [],
                "summary": {
                    "status": "NORMAL",
                    "timestamp": "2026-08-08T11:23:27Z",
                    "total_facilities_monitored": 1
                }
            }
        }

        with patch.object(AIServiceClient, "_make_request", return_value=mock_response) as mock_req:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.get(
                    "/prediction/dashboard",
                    params={
                        "facility_id": "1",
                        "eta_minutes": 20,
                    }
                )
                self.assertEqual(resp.status_code, 200)
                data = resp.json()
                self.assertEqual(data["occupancy"]["facility_id"], "1")
                self.assertEqual(data["forecast"]["forecast_30m"], 80.0)
                self.assertEqual(data["availability"]["risk_level"], "LOW")
                mock_req.assert_called_once()

    async def test_backend_dashboard_endpoint_degraded_fallback(self):
        """Test backend dashboard fallback logic when AI Service is completely down."""
        mock_error = {
            "success": False,
            "error": {
                "code": "AI_SERVICE_UNAVAILABLE",
                "message": "The AI Service is currently unreachable or down.",
                "status_code": 503
            }
        }

        with patch.object(AIServiceClient, "_make_request", return_value=mock_error):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.get(
                    "/prediction/dashboard",
                    params={
                        "facility_id": "1",
                        "eta_minutes": 20,
                    }
                )
                self.assertEqual(resp.status_code, 200)
                data = resp.json()
                # Verify fallback structures are present
                self.assertIn("occupancy", data)
                self.assertIn("forecast", data)
                self.assertIn("availability", data)
                self.assertIn("insights", data)
                # Verify fallback insight indicates offline status
                self.assertEqual(data["insights"][0]["type"], "system")
                self.assertEqual(data["insights"][0]["severity"], "WARNING")
                self.assertIn("AI Service is offline", data["insights"][0]["message"])
