import unittest
from unittest.mock import patch
import httpx
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.database.session import get_async_session
from backend.app.models.base import Base
from backend.app.models.parking import ParkingFacility, ParkingSlot
from backend.app.services.ai_service_client import AIServiceClient, ai_service_client

# Setup an in-memory SQLite database specifically for test isolated runs
DATABASE_URL_TEST = "sqlite+aiosqlite:///:memory:"

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

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


class TestE2EPredictionIntegration(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        app.dependency_overrides[get_async_session] = override_get_async_session
            
        # Seed the database
        async with AsyncSessionLocalTest() as session:
            # Seed a facility
            facility1 = ParkingFacility(id=1, name="Downtown Central Parking", address="123 Street", city="Bangalore", is_active=True)
            facility2 = ParkingFacility(id=2, name="City Mall Parking", address="456 Avenue", city="Bangalore", is_active=True)
            session.add_all([facility1, facility2])
            
            # Seed slots for facility 1 (10 slots total, 3 occupied)
            for i in range(10):
                slot = ParkingSlot(id=i+1, facility_id=1, slot_number=f"A-{i+1}", is_available=(i >= 3))
                session.add(slot)
                
            # Seed slots for facility 2 (10 slots total, 8 occupied)
            for i in range(10):
                slot = ParkingSlot(id=i+11, facility_id=2, slot_number=f"B-{i+1}", is_available=(i >= 8))
                session.add(slot)
                
            await session.commit()

    async def asyncTearDown(self) -> None:
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine_test.dispose()
        app.dependency_overrides.clear()

    async def test_1_e2e_recommendation_success_path(self):
        """Test successful recommendations E2E path (forwarding AI Service response)."""
        mock_ai_response = {
            "success": True,
            "data": {
                "recommendations": [
                    {
                        "rank": 1,
                        "facility_id": "1",
                        "facility_name": "Downtown Central Parking",
                        "recommendation_score": 95.0,
                        "availability_probability": 85.0,
                        "current_occupancy": 30.0,
                        "forecast_occupancy": 32.0,
                        "distance_km": 0.5,
                        "walking_distance_m": 600,
                        "estimated_cost": 20.0,
                        "queue_wait_minutes": 1.0,
                        "occupancy_risk": "LOW",
                        "confidence": 98.0,
                        "reason": "Top scoring option."
                    }
                ],
                "total_candidates": 1,
                "returned_results": 1
            }
        }
        
        with patch.object(AIServiceClient, "_make_request", return_value=mock_ai_response):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                payload = {
                    "latitude": 12.9716,
                    "longitude": 77.5946,
                    "eta_minutes": 20,
                    "max_distance_km": 5.0,
                    "max_results": 5
                }
                resp = await ac.post("/prediction/recommendations", json=payload)
                self.assertEqual(resp.status_code, 200)
                data = resp.json()
                self.assertEqual(data["returned_results"], 1)
                self.assertEqual(data["recommendations"][0]["facility_id"], "1")

    async def test_2_e2e_decision_success_path(self):
        """Test successful intelligence decision E2E path."""
        mock_ai_response = {
            "success": True,
            "data": {
                "facility_id": "1",
                "eta_minutes": 20,
                "predicted_occupancy": 32.0,
                "predicted_available_slots": 7,
                "availability_probability": 0.85,
                "queue_wait_minutes": 1.0,
                "confidence": 0.98,
                "recommendation": "GOOD_CHOICE",
                "alternative_facilities": [],
                "reasoning": ["Predicted occupancy remains below critical threshold"],
                "prediction_status": "SUCCESS"
            }
        }
        
        with patch.object(AIServiceClient, "_make_request", return_value=mock_ai_response):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.get("/prediction/decision/1?eta_minutes=20")
                self.assertEqual(resp.status_code, 200)
                data = resp.json()
                self.assertEqual(data["recommendation"], "GOOD_CHOICE")
                self.assertEqual(data["prediction_status"], "SUCCESS")

    async def test_3_client_retry_and_backoff(self):
        """Test that AIServiceClient retries connection failures up to configured count."""
        call_count = 0
        
        # Side effect raises TimeoutException on first two tries, then returns success
        def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise httpx.TimeoutException("Connection timed out")
            return mock_response
            
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = lambda: {"success": True, "test": "ok"}
        
        # Test client with retry count 3
        client = AIServiceClient(base_url="http://mock-ai:8001", timeout=1.0, retry_count=3)
        
        with patch("httpx.AsyncClient.request", side_effect=mock_request), \
             patch("asyncio.sleep", return_value=None) as mock_sleep:
            res = await client._make_request("GET", "/test")
            self.assertTrue(res["success"])
            self.assertEqual(call_count, 3) # 2 failures, 3rd try succeeds
            self.assertEqual(mock_sleep.call_count, 2)

    async def test_4_e2e_db_fallback_occupancy(self):
        """Test database-driven fallback for occupancy forecast when AI Service is unavailable."""
        mock_ai_failure = {
            "success": False,
            "error": {
                "code": "AI_SERVICE_UNAVAILABLE",
                "message": "AI Service unreachable."
            }
        }
        
        with patch.object(AIServiceClient, "_make_request", return_value=mock_ai_failure):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                # Query occupancy for facility 1 (seeded with 3 occupied slots / 10 total slots = 30%)
                resp = await ac.get("/prediction/occupancy/1?horizon_minutes=15")
                self.assertEqual(resp.status_code, 200)
                data = resp.json()
                
                self.assertEqual(data["current_occupancy"], 30.0)
                self.assertEqual(data["prediction_15"], 30.0)
                self.assertEqual(data["prediction_status"], "DEGRADED_FALLBACK")
                self.assertEqual(data["confidence"], 0.0)

    async def test_5_e2e_db_fallback_availability(self):
        """Test database-driven fallback for availability forecast when AI Service is unavailable."""
        mock_ai_failure = {
            "success": False,
            "error": {
                "code": "AI_SERVICE_UNAVAILABLE",
                "message": "AI Service unreachable."
            }
        }
        
        with patch.object(AIServiceClient, "_make_request", return_value=mock_ai_failure):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                # Query availability for facility 2 (seeded with 8 occupied slots / 10 total slots = 80%)
                resp = await ac.get("/prediction/availability/2?eta_minutes=20")
                self.assertEqual(resp.status_code, 200)
                data = resp.json()
                
                self.assertEqual(data["current_occupancy"], 80.0)
                self.assertEqual(data["expected_free_slots"], 2)
                self.assertEqual(data["availability_probability"], 20.0) # 2 free / 10 slots
                self.assertEqual(data["occupancy_risk"], "MEDIUM")
                self.assertEqual(data["risk_level"], "MEDIUM_RISK")
                self.assertEqual(data["prediction_status"], "DEGRADED_FALLBACK")

    async def test_6_e2e_db_fallback_recommendations(self):
        """Test database-driven fallback for recommendations when AI Service is unavailable."""
        mock_ai_failure = {
            "success": False,
            "error": {
                "code": "AI_SERVICE_UNAVAILABLE",
                "message": "AI Service unreachable."
            }
        }
        
        with patch.object(AIServiceClient, "_make_request", return_value=mock_ai_failure):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                payload = {
                    "latitude": 12.9716,
                    "longitude": 77.5946,
                    "eta_minutes": 20,
                    "max_distance_km": 5.0,
                    "max_results": 5
                }
                resp = await ac.post("/prediction/recommendations", json=payload)
                self.assertEqual(resp.status_code, 200)
                data = resp.json()
                
                # Check that both facility 1 and 2 are returned and ranked correctly based on distance and occupancy
                self.assertEqual(data["returned_results"], 2)
                self.assertEqual(data["recommendations"][0]["facility_id"], "1") # Closer / lower occupancy
                self.assertEqual(data["recommendations"][1]["facility_id"], "2")
                self.assertIn("Fallback recommendation", data["recommendations"][0]["reason"])

    async def test_7_e2e_db_fallback_decision(self):
        """Test database-driven fallback for unified decision when AI Service is unavailable."""
        mock_ai_failure = {
            "success": False,
            "error": {
                "code": "AI_SERVICE_UNAVAILABLE",
                "message": "AI Service unreachable."
            }
        }
        
        with patch.object(AIServiceClient, "_make_request", return_value=mock_ai_failure):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.get("/prediction/decision/1?eta_minutes=20")
                self.assertEqual(resp.status_code, 200)
                data = resp.json()
                
                self.assertEqual(data["facility_id"], "1")
                self.assertEqual(data["predicted_occupancy"], 30.0)
                self.assertEqual(data["predicted_available_slots"], 7)
                self.assertEqual(data["availability_probability"], 0.70) # 7 free slots / 10 total = 70% (0.70)
                self.assertEqual(data["recommendation"], "GOOD_CHOICE")
                self.assertEqual(data["prediction_status"], "DEGRADED_FALLBACK")
                self.assertEqual(len(data["alternative_facilities"]), 1)
                self.assertEqual(data["alternative_facilities"][0]["facility_id"], "2")


from unittest.mock import MagicMock
