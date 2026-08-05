"""
Functional validation tests for the ParkZenith AI intelligence layer.
Runs against the seeded database (using either PostgreSQL in prod or local SQLite in dev).
Measures latency and checks response validity of occupancy, availability, recommendations, and queue models.
"""

import asyncio
import os
import time
import unittest
from sqlalchemy.ext.asyncio import AsyncSession

from ai_service.config.settings import settings
from ai_service.database.session import AsyncSessionFactory
from ai_service.api.deps import (
    get_forecasting_service,
    get_availability_service,
    get_recommendation_service,
    get_queue_service,
)


class TestAIProductionValidation(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        print(f"\n[DEBUG] CWD: {os.getcwd()}")
        print(f"[DEBUG] DATABASE_URL: {settings.DATABASE_URL}")

        self.db_session: AsyncSession = AsyncSessionFactory()
        self.forecasting = get_forecasting_service()
        self.availability = get_availability_service()
        self.recommendation = get_recommendation_service()
        self.queue_service = get_queue_service()

        # Eagerly load forecasting model if not loaded yet
        if not self.forecasting.forecaster.is_loaded:
            self.forecasting.forecaster.load()

    async def asyncTearDown(self) -> None:
        await self.db_session.close()

    async def test_1_occupancy_forecasting_validation(self):
        """Validate forecasting logic and response latencies."""
        # Ensure we have a model loaded
        self.assertTrue(self.forecasting.forecaster.is_loaded, "Model not loaded!")

        start_time = time.time()
        # Query occupancy forecast for facility 1 and horizon 15 minutes
        result = await self.forecasting.forecaster.get_or_train_custom_horizon(
            db_session=self.db_session,
            horizon_minutes=15
        )
        duration_ms = (time.time() - start_time) * 1000

        self.assertIn("best_model_name", result)
        self.assertIn("metrics", result)
        self.assertLess(duration_ms, 5000.0, f"Occupancy forecasting took too long: {duration_ms:.2f}ms")
        print(f"\n[AI Validation] Occupancy Forecasting Latency: {duration_ms:.2f}ms")

    async def test_2_availability_prediction_validation(self):
        """Validate availability prediction outputs and response latencies."""
        start_time = time.time()
        # Get availability for facility "1" with ETA 20 minutes
        result = await self.availability.predict_facility_availability(
            db=self.db_session,
            facility_id_raw="1",
            eta_minutes=20
        )
        duration_ms = (time.time() - start_time) * 1000

        self.assertEqual(result["facility_id"], "1")
        self.assertGreaterEqual(result["availability_probability"], 0.0)
        self.assertLessEqual(result["availability_probability"], 100.0)
        self.assertIn(result["occupancy_risk"], ["LOW", "MEDIUM", "HIGH"])
        self.assertLess(duration_ms, 5000.0, f"Availability prediction took too long: {duration_ms:.2f}ms")
        print(f"[AI Validation] Availability Prediction Latency: {duration_ms:.2f}ms")

    async def test_3_recommendation_engine_validation(self):
        """Validate recommendation consistency, sorting, and response latencies."""
        start_time = time.time()
        # Generate recommendations near coordinates
        results = await self.recommendation.get_recommendations(
            db=self.db_session,
            user_latitude=12.9716,
            user_longitude=77.5946,
            eta_minutes=20,
            max_results=3
        )
        duration_ms = (time.time() - start_time) * 1000

        recommendations = results["recommendations"]
        self.assertGreater(len(recommendations), 0, "No recommendations returned!")
        # Validate sorting by rank
        ranks = [rec["rank"] for rec in recommendations]
        self.assertEqual(ranks, sorted(ranks), "Recommendations not sorted by rank!")
        
        # Verify first recommendation properties
        first = recommendations[0]
        self.assertIn("recommendation_score", first)
        self.assertIn("facility_id", first)
        self.assertLess(duration_ms, 5000.0, f"Recommendation generation took too long: {duration_ms:.2f}ms")
        print(f"[AI Validation] Recommendation Engine Latency: {duration_ms:.2f}ms")

    async def test_4_virtual_queue_intelligence_validation(self):
        """Validate queue estimations, predictions, and response latencies."""
        # Enqueue driver 1 to ensure a driver is in queue
        try:
            await self.queue_service.enqueue_user(self.db_session, "1", "driver1")
        except Exception:
            pass # ignore duplicates

        start_time = time.time()
        # Check current queue state
        queue_state = await self.queue_service.get_queue_prediction(self.db_session, "1", eta_minutes=0)
        
        # Run prediction
        pred_res = await self.queue_service.get_queue_prediction(
            db=self.db_session,
            facility_id_raw="1",
            eta_minutes=20
        )
        duration_ms = (time.time() - start_time) * 1000

        self.assertGreaterEqual(queue_state["predicted_queue_length"], 0)
        self.assertGreaterEqual(pred_res["predicted_queue_length"], 0.0)
        self.assertGreaterEqual(pred_res["expected_wait_minutes"], 0.0)
        self.assertLess(duration_ms, 5000.0, f"Queue prediction took too long: {duration_ms:.2f}ms")
        print(f"[AI Validation] Virtual Queue Intelligence Latency: {duration_ms:.2f}ms")
