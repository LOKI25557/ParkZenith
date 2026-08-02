import unittest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport, ConnectError, TimeoutException
from fastapi import HTTPException

from backend.app.main import app
from backend.app.services.ai_service_client import AIServiceClient, ai_service_client


class TestAIServiceIntegration(unittest.IsolatedAsyncioTestCase):

    async def test_client_success_occupancy(self):
        """Test successful occupancy forecast retrieval."""
        mock_response = {
            "success": True,
            "data": {
                "facility_id": 1,
                "current_occupancy": 75.0,
                "prediction_15": 80.0,
                "prediction_30": 85.0,
                "prediction_60": 90.0,
                "confidence": 98.0
            }
        }
        with patch.object(AIServiceClient, "_make_request", return_value=mock_response) as mock_req:
            res = await ai_service_client.get_occupancy_prediction(facility_id=1, horizon_minutes=15)
            self.assertTrue(res["success"])
            self.assertEqual(res["data"]["prediction_15"], 80.0)
            mock_req.assert_called_once_with("GET", "/forecast/15", params={"facility_id": 1})

    async def test_client_custom_occupancy(self):
        """Test successful custom occupancy forecast retrieval."""
        mock_response = {
            "success": True,
            "data": {
                "facility_id": 1,
                "current_occupancy": 75.0,
                "prediction_custom": 82.5,
                "confidence": 95.0
            }
        }
        with patch.object(AIServiceClient, "_make_request", return_value=mock_response) as mock_req:
            res = await ai_service_client.get_occupancy_prediction(facility_id=1, horizon_minutes=45)
            self.assertTrue(res["success"])
            self.assertEqual(res["data"]["prediction_custom"], 82.5)
            mock_req.assert_called_once_with("POST", "/forecast/custom", json_data={"facility_id": 1, "target_minutes": 45})

    async def test_client_error_missing_facility(self):
        """Test client handles missing facility error properly."""
        mock_error = {
            "success": False,
            "error": {
                "code": "MISSING_FACILITY",
                "message": "Facility FAC-XYZ has no historical records.",
                "status_code": 404
            }
        }
        with patch.object(AIServiceClient, "_make_request", return_value=mock_error):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.get("/prediction/availability/FAC-XYZ")
                self.assertEqual(resp.status_code, 404)
                self.assertIn("Facility FAC-XYZ has no historical records.", resp.json()["detail"])

    async def test_client_error_model_unavailable(self):
        """Test client handles model unavailable error properly."""
        mock_error = {
            "success": False,
            "error": {
                "code": "MODEL_UNAVAILABLE",
                "message": "Forecasting models have not been trained yet.",
                "status_code": 503
            }
        }
        with patch.object(AIServiceClient, "_make_request", return_value=mock_error):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.get("/prediction/occupancy/1?horizon_minutes=15")
                self.assertEqual(resp.status_code, 503)
                self.assertIn("Forecasting models have not been trained yet.", resp.json()["detail"])

    async def test_client_network_failure(self):
        """Test client handles unreachable AI Service."""
        with patch("httpx.AsyncClient.request", side_effect=ConnectError("Connection refused")):
            res = await ai_service_client.get_availability_prediction("FAC-1")
            self.assertFalse(res["success"])
            self.assertEqual(res["error"]["code"], "AI_SERVICE_UNAVAILABLE")

    async def test_client_timeout_failure(self):
        """Test client handles timeout properly."""
        with patch("httpx.AsyncClient.request", side_effect=TimeoutException("Connection timed out")):
            res = await ai_service_client.get_availability_prediction("FAC-1")
            self.assertFalse(res["success"])
            self.assertEqual(res["error"]["code"], "AI_SERVICE_TIMEOUT")

    async def test_backend_recommendations_endpoint(self):
        """Test recommendations endpoint integration on backend."""
        mock_response = {
            "success": True,
            "data": {
                "recommendations": [
                    {
                        "rank": 1,
                        "facility_id": "FAC-1",
                        "facility_name": "Main Lot",
                        "recommendation_score": 92.5,
                        "availability_probability": 85.0,
                        "current_occupancy": 60.0,
                        "forecast_occupancy": 70.0,
                        "distance_km": 0.8,
                        "walking_distance_m": 960,
                        "estimated_cost": 5.0,
                        "queue_wait_minutes": 2.0,
                        "occupancy_risk": "LOW",
                        "confidence": 95.0,
                        "reason": "Close with high availability."
                    }
                ],
                "total_candidates": 1,
                "returned_results": 1
            }
        }
        req_body = {
            "latitude": 12.9716,
            "longitude": 77.5946,
            "eta_minutes": 20,
            "max_distance_km": 5.0,
            "max_results": 5
        }
        with patch.object(AIServiceClient, "_make_request", return_value=mock_response):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.post("/prediction/recommendations", json=req_body)
                self.assertEqual(resp.status_code, 200)
                data = resp.json()
                self.assertEqual(len(data["recommendations"]), 1)
                self.assertEqual(data["recommendations"][0]["facility_id"], "FAC-1")

    async def test_backend_analytics_overview(self):
        """Test analytics overview endpoint integration on backend."""
        mock_response = {
            "success": True,
            "data": {
                "facility_id": "FAC-1",
                "summary": "Analytics Overview Data"
            }
        }
        with patch.object(AIServiceClient, "_make_request", return_value=mock_response):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.get("/analytics/overview?facility_id=FAC-1")
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp.json()["facility_id"], "FAC-1")

    async def test_backend_queue_predictions(self):
        """Test queue status and prediction integration on backend."""
        mock_response = {
            "success": True,
            "data": {
                "facility_id": "FAC-1",
                "current_queue_length": 3.0,
                "predicted_queue_length": 4.5,
                "expected_wait_minutes": 4.0
            }
        }
        with patch.object(AIServiceClient, "_make_request", return_value=mock_response) as mock_req:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                # 1. Test basic queue status (eta_minutes = None)
                resp = await ac.get("/prediction/queue/FAC-1")
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp.json()["current_queue_length"], 3.0)

                # 2. Test predicted queue
                resp2 = await ac.get("/prediction/queue/FAC-1?eta_minutes=30")
                self.assertEqual(resp2.status_code, 200)
                self.assertEqual(resp2.json()["predicted_queue_length"], 4.5)
