"""
Unit and integration tests for Phase 5 – Arrival Availability Prediction.
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

from ai_service.availability.calculator import (
    calculate_expected_free_slots,
    calculate_availability_probability,
    determine_occupancy_risk,
    determine_prediction_reliability,
)
from ai_service.availability.confidence import calculate_prediction_confidence
from ai_service.availability.estimator import (
    estimate_flow_occupancy_change,
    calculate_reservation_impact,
)
from ai_service.availability.predictor import predict_arrival_occupancy

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


# Setup dependency override
app.dependency_overrides[get_db_session] = override_get_db_session


class TestArrivalAvailability(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self) -> None:
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine_test.dispose()

    def test_calculator_functions(self) -> None:
        """Tests individual calculators for free slots, probability, risk, and reliability."""
        # 1. Expected Free Slots
        self.assertEqual(calculate_expected_free_slots(100, 60.4), 40)
        self.assertEqual(calculate_expected_free_slots(100, 105.0), 0)
        self.assertEqual(calculate_expected_free_slots(100, -2.0), 100)

        # 2. Availability Probability
        # If expected occupied is very low, probability available should be near 100%
        prob_high = calculate_availability_probability(100, 10.0, 20)
        self.assertGreater(prob_high, 95.0)

        # If expected occupied is near capacity, probability available should be lower
        prob_mid = calculate_availability_probability(100, 95.0, 20)
        self.assertLess(prob_mid, 80.0)

        # 3. Occupancy Risk
        self.assertEqual(determine_occupancy_risk(95.0, 75.0), "HIGH")
        self.assertEqual(determine_occupancy_risk(75.0, 30.0), "MEDIUM")
        self.assertEqual(determine_occupancy_risk(50.0, 5.0), "LOW")

        # 4. Prediction Reliability
        self.assertEqual(determine_prediction_reliability(90.0), "HIGH")
        self.assertEqual(determine_prediction_reliability(75.0), "MEDIUM")
        self.assertEqual(determine_prediction_reliability(50.0), "LOW")

    def test_estimator_functions(self) -> None:
        """Tests estimator computations for vehicle flow changes and reservation impact."""
        # Flow occupancy change: arrivals rate = 12/hr, departures rate = 6/hr, ETA = 30 mins (0.5 hr)
        # expected net flow change = (12 - 6) * 0.5 = +3
        flow_change = estimate_flow_occupancy_change(12.0, 6.0, 30)
        self.assertEqual(flow_change, 3.0)

        # Reservation impact: 5 incoming, 2 outgoing -> net +3
        res_impact = calculate_reservation_impact(5, 2)
        self.assertEqual(res_impact, 3)

    def test_confidence_decay_and_penalties(self) -> None:
        """Tests confidence calculation under varying ETAs and forecasting models availability."""
        # Standard case: 0 ETA, 100 records
        conf_0 = calculate_prediction_confidence(0, 95.0, 100)
        self.assertEqual(conf_0, 95.0)

        # Confidence should decay as ETA increases
        conf_60 = calculate_prediction_confidence(60, 95.0, 100)
        self.assertLess(conf_60, conf_0)

        # Penalty when forecasting model is missing
        conf_no_model = calculate_prediction_confidence(0, None, 100)
        self.assertEqual(conf_no_model, 75.0)

        # Penalty when historical records are sparse
        conf_no_data = calculate_prediction_confidence(0, 95.0, 5)
        self.assertLess(conf_no_data, conf_0)

    def test_predictor_blending(self) -> None:
        """Tests ML forecast and flow-based prediction blending logic."""
        # Capacity: 100, current occupied: 50, flow change: +5, res impact: +5.
        # Flow prediction: 50 + 5 + 5 = 60
        # ML forecast prediction: 80% occupancy -> 80 slots occupied.
        
        # ETA = 0 -> weight_ml = 0.0 -> returns flow prediction (which is just current occupied if flow/res are 0)
        pred_0 = predict_arrival_occupancy(100, 50, 0.0, 0, forecast_occupancy_pct=80.0, eta_minutes=0)
        self.assertEqual(pred_0, 50.0)

        # ETA = 30 -> weight_ml = 0.5 -> blends flow prediction (60) and ML prediction (80) -> 70
        pred_30 = predict_arrival_occupancy(100, 50, 5.0, 5, forecast_occupancy_pct=80.0, eta_minutes=30)
        self.assertEqual(pred_30, 70.0)

        # ETA = 60 -> weight_ml = 1.0 -> returns ML forecast prediction -> 80
        pred_60 = predict_arrival_occupancy(100, 50, 5.0, 5, forecast_occupancy_pct=80.0, eta_minutes=60)
        self.assertEqual(pred_60, 80.0)

        # Fallback case: ML forecast missing -> returns flow-based prediction
        pred_fallback = predict_arrival_occupancy(100, 50, 5.0, 5, forecast_occupancy_pct=None, eta_minutes=30)
        self.assertEqual(pred_fallback, 60.0)

    async def _populate_test_records(self, session: AsyncSession) -> None:
        """Populates database with test occupancy, session, and reservation history."""
        now = datetime.now(timezone.utc)
        
        # Facility 1 occupancy logs
        for i in range(10):
            occ = OccupancyHistory(
                facility_id="1",
                zone_id="ZONE-A",
                total_slots=100,
                occupied_slots=60 + i,
                available_slots=40 - i,
                occupancy_percentage=60.0 + i,
                collected_at=now - timedelta(minutes=10 * i)
            )
            session.add(occ)

        # Facility 1 session logs to generate flow rate
        # Let's add 5 sessions checked in during the current hour
        for i in range(5):
            sess = ParkingSessionHistory(
                session_id=f"SESS-AV-{i}",
                facility_id="1",
                vehicle_type="CAR",
                check_in_time=now - timedelta(hours=24 * i),  # spread across days at same hour
                check_out_time=now - timedelta(hours=24 * i) + timedelta(hours=1),
                duration_minutes=60.0,
                parking_fee=5.0,
                collected_at=now
            )
            session.add(sess)

        # Facility 1 upcoming reservations (within next 30 minutes)
        # Starting soon
        res_in = ReservationHistory(
            reservation_id="RES-AV-IN",
            facility_id="1",
            slot_id="SLOT-A1",
            reservation_status="CONFIRMED",
            reservation_start=now + timedelta(minutes=15),
            reservation_end=now + timedelta(minutes=45),
            duration_minutes=30.0,
            collected_at=now
        )
        # Ending soon
        res_out = ReservationHistory(
            reservation_id="RES-AV-OUT",
            facility_id="1",
            slot_id="SLOT-A2",
            reservation_status="CONFIRMED",
            reservation_start=now - timedelta(minutes=15),
            reservation_end=now + timedelta(minutes=15),
            duration_minutes=30.0,
            collected_at=now
        )
        session.add(res_in)
        session.add(res_out)
        await session.commit()

    async def test_availability_api_endpoints(self) -> None:
        """Verifies status, prediction, summary endpoints and error conditions."""
        async with AsyncSessionLocalTest() as session:
            await self._populate_test_records(session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Test status check
            resp = await client.get("/availability/status")
            self.assertEqual(resp.status_code, 200)
            status_data = resp.json()
            self.assertIn("status", status_data)
            self.assertIn("forecasting_service_ready", status_data)

            # 2. Test predict POST route
            req_body = {
                "facility_id": 1,
                "eta_minutes": 20
            }
            resp = await client.post("/availability/predict", json=req_body)
            self.assertEqual(resp.status_code, 200)
            pred_data = resp.json()
            self.assertEqual(pred_data["facility_id"], 1)
            self.assertEqual(pred_data["eta_minutes"], 20)
            self.assertIn("current_occupancy", pred_data)
            self.assertIn("forecast_occupancy", pred_data)
            self.assertIn("expected_free_slots", pred_data)
            self.assertIn("availability_probability", pred_data)
            self.assertIn("occupancy_risk", pred_data)
            self.assertIn("confidence", pred_data)

            # 3. Test get facility_id route
            resp = await client.get("/availability/1?eta_minutes=20")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json()["facility_id"], "1")

            # 4. Test summary route
            resp = await client.get("/availability/summary?eta_minutes=20")
            self.assertEqual(resp.status_code, 200)
            summary = resp.json()
            self.assertEqual(summary["total_facilities_predicted"], 1)
            self.assertGreater(len(summary["predictions"]), 0)

            # 5. Error case: Invalid ETA (negative value)
            resp = await client.get("/availability/1?eta_minutes=-10")
            self.assertEqual(resp.status_code, 422)  # Pydantic validation error or status code 400

            # 6. Error case: Unknown facility
            resp = await client.get("/availability/999?eta_minutes=20")
            self.assertEqual(resp.status_code, 404)
            detail = resp.json()["detail"].lower() if "detail" in resp.json() else ""
            self.assertTrue("not found" in detail or "no historical records" in detail)
