"""
Unit and integration tests for Phase 7 – Queue Prediction & Congestion Intelligence.
"""

import os
import unittest
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from ai_service.main import app
from ai_service.database.session import get_db_session
from ai_service.database.base import Base
from ai_service.models.occupancy import OccupancyHistory
from ai_service.models.reservation import ReservationHistory
from ai_service.models.session import ParkingSessionHistory

from ai_service.queue.estimator import estimate_current_queue
from ai_service.queue.predictor import predict_future_queue
from ai_service.queue.waiting_time import estimate_waiting_time
from ai_service.queue.congestion import classify_congestion
from ai_service.queue.queue_engine import QueueEngine
from ai_service.services.queue_service import QueueService
from ai_service.services.recommendation_service import RecommendationService

# Setup test DB URL
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


class TestQueuePrediction(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        app.dependency_overrides[get_db_session] = override_get_db_session

    async def asyncTearDown(self) -> None:
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine_test.dispose()
        app.dependency_overrides.clear()

    # --- Unit Tests ---

    def test_1_basic_queue_estimation(self) -> None:
        """1. Basic queue estimation."""
        queue = estimate_current_queue(
            capacity=100,
            occupied_slots=80,
            arrival_rate_per_hour=240,  # 4/min, throughput is 3/min -> gate queue builds
            departure_rate_per_hour=60,
        )
        self.assertGreater(queue, 0.0)

    def test_2_zero_queue(self) -> None:
        """2. Zero queue."""
        queue = estimate_current_queue(
            capacity=100,
            occupied_slots=20,
            arrival_rate_per_hour=60,  # 1/min, throughput is 3/min
            departure_rate_per_hour=60,
        )
        self.assertEqual(queue, 0.0)

    def test_3_high_queue(self) -> None:
        """3. High queue."""
        queue = estimate_current_queue(
            capacity=100,
            occupied_slots=98,  # full facility -> Lot full queue forms
            arrival_rate_per_hour=300,
            departure_rate_per_hour=30,
        )
        self.assertGreater(queue, 10.0)

    def test_4_waiting_time_calculation(self) -> None:
        """4. Waiting-time calculation."""
        # Queue length = 6, throughput = 3/min, available slots = 10 -> Wait time = 2 mins
        wait = estimate_waiting_time(
            queue_length=6.0,
            capacity=100,
            occupied_slots=90,
            departure_rate_per_hour=60,
            entry_throughput_per_minute=3.0,
        )
        self.assertEqual(wait, 2.0)

    def test_5_queue_increasing(self) -> None:
        """5. Queue increasing trend."""
        _, _, _, trend = predict_future_queue(
            current_queue_length=2.0,
            arrival_rate_per_hour=80,
            departure_rate_per_hour=76,  # net growth = +4/hr
            eta_minutes=20,
            capacity=100,
            occupied_slots=50,
        )
        self.assertEqual(trend, "INCREASING")

    def test_6_queue_decreasing(self) -> None:
        """6. Queue decreasing trend."""
        _, _, _, trend = predict_future_queue(
            current_queue_length=5.0,
            arrival_rate_per_hour=40,
            departure_rate_per_hour=50,  # net growth = -10/hr
            eta_minutes=20,
            capacity=100,
            occupied_slots=50,
        )
        self.assertEqual(trend, "DECREASING")

    def test_7_stable_queue(self) -> None:
        """7. Stable queue trend."""
        _, _, _, trend = predict_future_queue(
            current_queue_length=1.0,
            arrival_rate_per_hour=60,
            departure_rate_per_hour=60,  # net growth = 0/hr
            eta_minutes=20,
            capacity=100,
            occupied_slots=50,
        )
        self.assertEqual(trend, "STABLE")

    def test_8_rapidly_increasing_queue(self) -> None:
        """8. Rapidly increasing queue trend."""
        _, _, _, trend = predict_future_queue(
            current_queue_length=2.0,
            arrival_rate_per_hour=150,
            departure_rate_per_hour=30,  # net growth = +120/hr
            eta_minutes=20,
            capacity=100,
            occupied_slots=50,
        )
        self.assertEqual(trend, "RAPIDLY_INCREASING")

    def test_9_low_congestion(self) -> None:
        """9. LOW congestion."""
        level = classify_congestion(
            queue_length=0.5,
            capacity=100,
            occupied_slots=40,
            waiting_time_minutes=0.5,
        )
        self.assertEqual(level, "LOW")

    def test_10_moderate_congestion(self) -> None:
        """10. MODERATE congestion."""
        level = classify_congestion(
            queue_length=3.0,
            capacity=100,
            occupied_slots=75,
            waiting_time_minutes=3.0,
        )
        self.assertEqual(level, "MODERATE")

    def test_11_high_congestion(self) -> None:
        """11. HIGH congestion."""
        level = classify_congestion(
            queue_length=6.0,
            capacity=100,
            occupied_slots=88,
            waiting_time_minutes=6.0,
        )
        self.assertEqual(level, "HIGH")

    def test_12_severe_congestion(self) -> None:
        """12. SEVERE congestion."""
        level = classify_congestion(
            queue_length=12.0,
            capacity=100,
            occupied_slots=96,
            waiting_time_minutes=12.0,
        )
        self.assertEqual(level, "SEVERE")

    def test_13_confidence_calculation(self) -> None:
        """13. Confidence calculation."""
        conf = QueueEngine.calculate_confidence(
            has_current_occupancy=True,
            has_historical_sessions=True,
            session_data_count=15,
            has_reservations=True,
        )
        self.assertEqual(conf, 100.0)

    def test_14_missing_historical_data(self) -> None:
        """14. Missing historical data penalty."""
        conf = QueueEngine.calculate_confidence(
            has_current_occupancy=True,
            has_historical_sessions=False,
            session_data_count=0,
            has_reservations=True,
        )
        self.assertEqual(conf, 80.0)

    def test_15_missing_occupancy_data(self) -> None:
        """15. Missing occupancy data penalty."""
        conf = QueueEngine.calculate_confidence(
            has_current_occupancy=False,
            has_historical_sessions=True,
            session_data_count=20,
            has_reservations=True,
        )
        self.assertEqual(conf, 80.0)

    def test_16_zero_facility_capacity(self) -> None:
        """16. Zero facility capacity handling."""
        queue = estimate_current_queue(
            capacity=0,
            occupied_slots=0,
            arrival_rate_per_hour=100,
            departure_rate_per_hour=100,
        )
        self.assertEqual(queue, 0.0)

    def test_17_full_facility(self) -> None:
        """17. Full facility queue accumulation."""
        queue = estimate_current_queue(
            capacity=100,
            occupied_slots=100,
            arrival_rate_per_hour=120,
            departure_rate_per_hour=30,
        )
        self.assertGreater(queue, 0.0)

    def test_18_empty_facility(self) -> None:
        """18. Empty facility."""
        queue = estimate_current_queue(
            capacity=100,
            occupied_slots=0,
            arrival_rate_per_hour=60,
            departure_rate_per_hour=60,
        )
        self.assertEqual(queue, 0.0)

    def test_19_invalid_input_handling(self) -> None:
        """19. Invalid input handling (clamping negative values)."""
        queue = estimate_current_queue(
            capacity=-50,
            occupied_slots=-10,
            arrival_rate_per_hour=-100,
            departure_rate_per_hour=-50,
        )
        self.assertEqual(queue, 0.0)

    # --- Integration Tests ---

    async def _populate_test_records(self, session: AsyncSession) -> None:
        """Populates database with test occupancy, session, and reservation history."""
        now = datetime.now(timezone.utc)
        
        # Occupancy logs for facility_id="FAC-Q"
        occ = OccupancyHistory(
            facility_id="FAC-Q",
            zone_id="ZONE-Q",
            total_slots=100,
            occupied_slots=80,
            available_slots=20,
            occupancy_percentage=80.0,
            collected_at=now
        )
        session.add(occ)

        # Session logs to generate flow rate
        for i in range(5):
            sess = ParkingSessionHistory(
                session_id=f"SESS-Q-{i}",
                facility_id="FAC-Q",
                vehicle_type="CAR",
                check_in_time=now - timedelta(hours=24 * i),  # same hour on previous days
                check_out_time=now - timedelta(hours=24 * i) + timedelta(hours=1),
                duration_minutes=60.0,
                parking_fee=5.0,
                collected_at=now
            )
            session.add(sess)

        # Reservations
        res = ReservationHistory(
            reservation_id="RES-Q-1",
            facility_id="FAC-Q",
            slot_id="SLOT-Q1",
            reservation_status="CONFIRMED",
            reservation_start=now + timedelta(minutes=10),
            reservation_end=now + timedelta(minutes=40),
            duration_minutes=30.0,
            collected_at=now
        )
        session.add(res)
        await session.commit()

    async def test_20_service_integration(self) -> None:
        """20. Service integration."""
        async with AsyncSessionLocalTest() as session:
            await self._populate_test_records(session)
            
            service = QueueService()
            result = await service.get_queue_prediction(session, "FAC-Q", eta_minutes=20)
            
            self.assertEqual(result["facility_id"], "FAC-Q")
            self.assertIn("current_queue_length", result)
            self.assertIn("expected_wait_minutes", result)
            self.assertIn("queue_trend", result)
            self.assertIn("congestion_level", result)

    async def test_21_api_response(self) -> None:
        """21. API response."""
        async with AsyncSessionLocalTest() as session:
            await self._populate_test_records(session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test current queue GET route
            resp = await client.get("/queue/FAC-Q")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["facility_id"], "FAC-Q")
            self.assertIn("current_queue_length", data)
            self.assertIn("expected_wait_minutes", data)
            self.assertIn("queue_trend", data)
            self.assertIn("congestion_level", data)

            # Test queue prediction GET route
            resp2 = await client.get("/queue/FAC-Q/prediction?eta_minutes=30")
            self.assertEqual(resp2.status_code, 200)
            data2 = resp2.json()
            self.assertEqual(data2["facility_id"], "FAC-Q")
            self.assertIn("predicted_queue_length", data2)

    async def test_22_phase_6_recommendation_integration(self) -> None:
        """22. Phase 6 recommendation integration."""
        async with AsyncSessionLocalTest() as session:
            await self._populate_test_records(session)
            
            rec_service = RecommendationService()
            results = await rec_service.get_recommendations(
                db=session,
                user_latitude=12.9716,
                user_longitude=77.5946,
                eta_minutes=20,
                max_results=5,
            )
            
            self.assertIn("recommendations", results)
            # Check that recommendations lists the facility FAC-Q with queue details
            found = False
            for rec in results["recommendations"]:
                if rec["facility_id"] == "FAC-Q":
                    found = True
                    self.assertIn("queue_wait_minutes", rec)
                    # wait time should be non-negative
                    self.assertGreaterEqual(rec["queue_wait_minutes"], 0.0)
            self.assertTrue(found, "FAC-Q should be recommended and contain queue information.")
