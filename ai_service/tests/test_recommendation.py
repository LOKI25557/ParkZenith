"""
Unit and integration tests for Phase 6 – Smart Recommendation Engine.
"""

import os
import unittest
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from pydantic import ValidationError

from ai_service.main import app
from ai_service.database.session import get_db_session
from ai_service.database.base import Base
from ai_service.models.occupancy import OccupancyHistory
from ai_service.models.reservation import ReservationHistory
from ai_service.models.session import ParkingSessionHistory

from ai_service.recommendation.weights import WeightConfiguration, get_facility_metadata
from ai_service.recommendation.filters import (
    calculate_distance_km,
    estimate_walking_distance_m,
    filter_candidate_facilities,
)
from ai_service.recommendation.scoring import RecommendationScorer
from ai_service.recommendation.ranking import rank_facilities
from ai_service.recommendation.explanation import generate_recommendation_reason
from ai_service.recommendation.recommendation_engine import RecommendationEngine

# Setup test DB URL in memory
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


async def override_get_db_session():
    async with AsyncSessionLocalTest() as session:
        yield session


class TestSmartRecommendationEngine(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        app.dependency_overrides[get_db_session] = override_get_db_session

    async def asyncTearDown(self) -> None:
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine_test.dispose()
        app.dependency_overrides.clear()  # Prevent polluting other tests

    def test_distance_calculation(self) -> None:
        """Verifies geographical Haversine calculations and walking estimates."""
        # Distance between identical coordinates is 0
        dist_zero = calculate_distance_km(12.9716, 77.5946, 12.9716, 77.5946)
        self.assertEqual(dist_zero, 0.0)

        # Distance from user to City Mall Parking
        dist_km = calculate_distance_km(12.9716, 77.5946, 12.9750, 77.6000)
        self.assertGreater(dist_km, 0.5)
        self.assertLess(dist_km, 1.5)

        # Walking distance estimate using road multiplier (e.g. 1.2)
        walking_m = estimate_walking_distance_m(dist_km)
        self.assertEqual(walking_m, int(dist_km * 1200.0))

    def test_weight_validation(self) -> None:
        """Verifies Pydantic weight validation rules (sum to 1.0, non-negative)."""
        # Valid weight config passes
        weights = WeightConfiguration(
            availability_probability=0.30,
            distance=0.20,
            forecast_occupancy=0.15,
            current_occupancy=0.10,
            walking_distance=0.10,
            historical_utilization=0.05,
            parking_cost=0.05,
            queue_congestion=0.05,
        )
        self.assertAlmostEqual(
            sum(
                [
                    weights.availability_probability,
                    weights.distance,
                    weights.forecast_occupancy,
                    weights.current_occupancy,
                    weights.walking_distance,
                    weights.historical_utilization,
                    weights.parking_cost,
                    weights.queue_congestion,
                ]
            ),
            1.0,
        )

        # Invalid weights (sum not equal to 1.0) should raise ValidationError
        with self.assertRaises(ValidationError):
            WeightConfiguration(
                availability_probability=0.5,
                distance=0.5,
                forecast_occupancy=0.5,
            )

        # Negative weights should raise ValidationError
        with self.assertRaises(ValidationError):
            WeightConfiguration(
                availability_probability=-0.1,
                distance=1.1,
            )

    def test_candidate_filtering(self) -> None:
        """Verifies filtering of inactive, out-of-radius, or capacity-zero facilities."""
        facilities = [
            # Active and valid
            {
                "facility_id": "FAC-1",
                "is_active": True,
                "latitude": 12.9716,
                "longitude": 77.5946,
                "total_slots": 100,
                "parking_type": "Standard",
                "accessibility": True,
            },
            # Inactive
            {
                "facility_id": "FAC-2",
                "is_active": False,
                "latitude": 12.9716,
                "longitude": 77.5946,
                "total_slots": 100,
                "parking_type": "Standard",
                "accessibility": True,
            },
            # Capacity zero
            {
                "facility_id": "FAC-3",
                "is_active": True,
                "latitude": 12.9716,
                "longitude": 77.5946,
                "total_slots": 0,
                "parking_type": "Standard",
                "accessibility": True,
            },
            # Far away
            {
                "facility_id": "FAC-4",
                "is_active": True,
                "latitude": 13.5000,
                "longitude": 78.5000,
                "total_slots": 100,
                "parking_type": "Standard",
                "accessibility": True,
            },
            # Accessibility mismatch
            {
                "facility_id": "FAC-5",
                "is_active": True,
                "latitude": 12.9716,
                "longitude": 77.5946,
                "total_slots": 100,
                "parking_type": "Standard",
                "accessibility": False,
            },
        ]

        # Standard filter with 5km radius
        filtered = filter_candidate_facilities(
            facilities=facilities,
            user_latitude=12.9716,
            user_longitude=77.5946,
            max_distance_km=5.0,
        )
        # FAC-1 and FAC-5 should pass (is_active, within radius, capacity > 0)
        self.assertEqual(len(filtered), 2)
        self.assertIn("FAC-1", [f["facility_id"] for f in filtered])
        self.assertIn("FAC-5", [f["facility_id"] for f in filtered])

        # Filter with accessibility requirement
        filtered_acc = filter_candidate_facilities(
            facilities=facilities,
            user_latitude=12.9716,
            user_longitude=77.5946,
            max_distance_km=5.0,
            accessibility_required=True,
        )
        self.assertEqual(len(filtered_acc), 1)
        self.assertEqual(filtered_acc[0]["facility_id"], "FAC-1")

    def test_score_normalization_and_ranges(self) -> None:
        """Verifies factors normalizer limits, extremes, and missing fallbacks."""
        scorer = RecommendationScorer()

        # Availability
        self.assertEqual(scorer.normalize_availability(0.0), 0.0)
        self.assertEqual(scorer.normalize_availability(100.0), 100.0)
        self.assertEqual(scorer.normalize_availability(None), 50.0)

        # Occupancy (lower occupancy is better)
        self.assertEqual(scorer.normalize_occupancy(0.0), 100.0)
        self.assertEqual(scorer.normalize_occupancy(100.0), 0.0)
        self.assertEqual(scorer.normalize_occupancy(None), 50.0)

        # Distance (closer distance is better)
        self.assertEqual(scorer.normalize_distance(0.0, 5.0), 100.0)
        self.assertEqual(scorer.normalize_distance(5.0, 5.0), 0.0)
        self.assertEqual(scorer.normalize_distance(10.0, 5.0), 0.0)  # clamped

        # Parking Cost (lower cost is better)
        self.assertEqual(scorer.normalize_cost(0.0, 50.0), 100.0)
        self.assertEqual(scorer.normalize_cost(50.0, 50.0), 0.0)
        self.assertEqual(scorer.normalize_cost(100.0, 50.0), 0.0)  # clamped

        # Utilization (optimal target is 60%)
        self.assertEqual(scorer.normalize_utilization(60.0), 100.0)
        self.assertEqual(scorer.normalize_utilization(50.0), 80.0)
        self.assertEqual(scorer.normalize_utilization(70.0), 80.0)
        self.assertEqual(scorer.normalize_utilization(10.0), 0.0)

        # Queue congestion (lower queue time is better)
        self.assertEqual(scorer.normalize_queue(0.0, 15.0), 100.0)
        self.assertEqual(scorer.normalize_queue(15.0, 15.0), 0.0)
        self.assertEqual(scorer.normalize_queue(None, 15.0), 100.0)  # assumes no queue if missing

    def test_deterministic_ranking(self) -> None:
        """Verifies deterministic sorting when scores are equal."""
        candidates = [
            {"facility_id": "B", "recommendation_score": 90.0, "distance_km": 2.0},
            {"facility_id": "A", "recommendation_score": 90.0, "distance_km": 1.0},
            {"facility_id": "C", "recommendation_score": 90.0, "distance_km": 1.0},
            {"facility_id": "D", "recommendation_score": 95.0, "distance_km": 3.0},
        ]
        ranked = rank_facilities(candidates)
        # Expected rank order:
        # 1. D (Score 95.0)
        # 2. A (Score 90.0, Distance 1.0, ID "A")
        # 3. C (Score 90.0, Distance 1.0, ID "C")
        # 4. B (Score 90.0, Distance 2.0, ID "B")
        self.assertEqual(ranked[0]["facility_id"], "D")
        self.assertEqual(ranked[1]["facility_id"], "A")
        self.assertEqual(ranked[2]["facility_id"], "C")
        self.assertEqual(ranked[3]["facility_id"], "B")
        self.assertEqual(ranked[0]["rank"], 1)
        self.assertEqual(ranked[3]["rank"], 4)

    def test_explanation_generation(self) -> None:
        """Checks tailored rationale explanations generated from factor scores."""
        scores_1 = {
            "availability_score": 95.0,
            "distance_score": 90.0,
            "forecast_score": 85.0,
            "walking_score": 10.0,
        }
        reason_1 = generate_recommendation_reason(scores_1)
        # Should pick the positive factors above 70
        self.assertIn("availability", reason_1)
        self.assertIn("distance", reason_1)

        scores_low = {
            "availability_score": 40.0,
            "distance_score": 30.0,
        }
        reason_low = generate_recommendation_reason(scores_low)
        # Should fallback to top 2 factors
        self.assertTrue(len(reason_low) > 0)

    async def _populate_test_records(self, session: AsyncSession) -> None:
        """Populates database with basic test records."""
        now = datetime.now(timezone.utc)
        # Facility "1" records
        for i in range(5):
            occ = OccupancyHistory(
                facility_id="1",
                zone_id="ZONE-A",
                total_slots=100,
                occupied_slots=40 + i,
                available_slots=60 - i,
                occupancy_percentage=40.0 + i,
                collected_at=now - timedelta(minutes=10 * i),
            )
            session.add(occ)

        # Facility "2" records
        for i in range(5):
            occ = OccupancyHistory(
                facility_id="2",
                zone_id="ZONE-B",
                total_slots=150,
                occupied_slots=80 + i,
                available_slots=70 - i,
                occupancy_percentage=53.33 + i,
                collected_at=now - timedelta(minutes=10 * i),
            )
            session.add(occ)

        await session.commit()

    async def test_recommendations_api(self) -> None:
        """Integration test for recommendation endpoints."""
        async with AsyncSessionLocalTest() as session:
            await self._populate_test_records(session)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            # 1. Status Check
            resp = await client.get("/recommendations/status")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertIn("status", data)
            self.assertIn("forecasting_service_ready", data)
            self.assertIn("availability_service_ready", data)

            # 2. Recommendations POST Check
            req_body = {
                "latitude": 12.9716,
                "longitude": 77.5946,
                "eta_minutes": 20,
                "max_distance_km": 5.0,
                "max_results": 5,
            }
            resp = await client.post("/recommendations", json=req_body)
            self.assertEqual(resp.status_code, 200, resp.text)
            data = resp.json()
            self.assertIn("recommendations", data)
            self.assertGreater(len(data["recommendations"]), 0)
            
            # Check fields
            top_rec = data["recommendations"][0]
            self.assertIn("rank", top_rec)
            self.assertIn("facility_id", top_rec)
            self.assertIn("recommendation_score", top_rec)
            self.assertIn("distance_km", top_rec)
            self.assertIn("walking_distance_m", top_rec)
            self.assertIn("reason", top_rec)

            # 3. Top Recommendations GET Check
            resp = await client.get(
                "/recommendations/top?latitude=12.9716&longitude=77.5946&eta_minutes=20"
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertGreater(len(data["recommendations"]), 0)

            # 4. Details for specific facility
            resp = await client.get(
                "/recommendations/1?latitude=12.9716&longitude=77.5946&eta_minutes=20"
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["facility_id"], "1")
            self.assertIn("recommendation_score", data)

            # 5. Ad-hoc Score calculation
            score_req = {
                "availability_probability": 85.0,
                "current_occupancy": 40.0,
                "forecast_occupancy": 45.0,
                "distance_km": 1.2,
                "walking_distance_m": 200,
                "hourly_rate": 20.0,
                "historical_utilization": 60.0,
                "queue_wait_minutes": 2,
                "max_distance_km": 5.0,
            }
            resp = await client.post("/recommendations/score", json=score_req)
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertIn("recommendation_score", data)
            self.assertTrue(0.0 <= data["recommendation_score"] <= 100.0)

            # 6. Error handling: invalid coordinates
            req_body_invalid = {
                "latitude": 95.0,  # invalid latitude
                "longitude": 77.5946,
                "eta_minutes": 20,
            }
            resp = await client.post("/recommendations", json=req_body_invalid)
            self.assertEqual(resp.status_code, 422)
