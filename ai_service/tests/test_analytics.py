"""
Verification tests for Phase 2 Analytics Engine.
"""

import os
import unittest
from datetime import datetime, timedelta, timezone, date
import pandas as pd
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from ai_service.main import app
from ai_service.config.settings import settings
from ai_service.database.session import engine, AsyncSessionFactory
from ai_service.database.base import Base

from ai_service.models.occupancy import OccupancyHistory
from ai_service.models.reservation import ReservationHistory
from ai_service.models.session import ParkingSessionHistory

from ai_service.analytics.occupancy import (
    calculate_current_occupancy,
    calculate_occupancy_metrics,
    calculate_hourly_trend,
    detect_peak_hours,
)
from ai_service.analytics.utilization import calculate_utilization_metrics
from ai_service.analytics.reservation import calculate_reservation_metrics
from ai_service.analytics.sessions import calculate_session_metrics
from ai_service.analytics.trends import calculate_occupancy_rolling_average


class TestAnalyticsEngine(unittest.IsolatedAsyncioTestCase):
    """
    Test suite verifying the Analytics Engine's business logic, Pandas modules, and FastAPI endpoints.
    """

    async def asyncSetUp(self) -> None:
        """Sets up database tables and initializes common test data."""
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

        self.now = datetime.now(timezone.utc)
        self.facility_id = "FAC-TEST-001"
        self.zone_id = "ZONE-A"

        # Define occupancy data
        self.occupancy_data = [
            OccupancyHistory(
                facility_id=self.facility_id,
                zone_id=self.zone_id,
                total_slots=100,
                occupied_slots=20,
                available_slots=80,
                occupancy_percentage=20.0,
                collected_at=self.now - timedelta(hours=3),
            ),
            OccupancyHistory(
                facility_id=self.facility_id,
                zone_id=self.zone_id,
                total_slots=100,
                occupied_slots=50,
                available_slots=50,
                occupancy_percentage=50.0,
                collected_at=self.now - timedelta(hours=2),
            ),
            OccupancyHistory(
                facility_id=self.facility_id,
                zone_id=self.zone_id,
                total_slots=100,
                occupied_slots=80,
                available_slots=20,
                occupancy_percentage=80.0,
                collected_at=self.now - timedelta(hours=1),
            ),
        ]

        # Define reservation data
        self.reservation_data = [
            ReservationHistory(
                reservation_id="RES-T01",
                facility_id=self.facility_id,
                slot_id="SLOT-A1",
                reservation_status="COMPLETED",
                reservation_start=self.now - timedelta(hours=4),
                reservation_end=self.now - timedelta(hours=3),
                duration_minutes=60.0,
                collected_at=self.now - timedelta(hours=4),
            ),
            ReservationHistory(
                reservation_id="RES-T02",
                facility_id=self.facility_id,
                slot_id="SLOT-A2",
                reservation_status="CANCELLED",
                reservation_start=self.now - timedelta(hours=2),
                reservation_end=self.now - timedelta(hours=1),
                duration_minutes=60.0,
                collected_at=self.now - timedelta(hours=2),
            ),
        ]

        # Define session data
        self.session_data = [
            ParkingSessionHistory(
                session_id="SESS-T01",
                facility_id=self.facility_id,
                vehicle_type="CAR",
                check_in_time=self.now - timedelta(hours=5),
                check_out_time=self.now - timedelta(hours=3),
                duration_minutes=120.0,
                parking_fee=10.0,
                collected_at=self.now - timedelta(hours=3),
            ),
            ParkingSessionHistory(
                session_id="SESS-T02",
                facility_id=self.facility_id,
                vehicle_type="EV",
                check_in_time=self.now - timedelta(hours=2),
                check_out_time=self.now - timedelta(hours=1),
                duration_minutes=60.0,
                parking_fee=5.0,
                collected_at=self.now - timedelta(hours=1),
            ),
        ]

    async def asyncTearDown(self) -> None:
        """Tears down database tables."""
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def _insert_test_data(self) -> None:
        """Inserts the test data into the database."""
        async with AsyncSessionFactory() as session:
            session.add_all(self.occupancy_data)
            session.add_all(self.reservation_data)
            session.add_all(self.session_data)
            await session.commit()

    def test_01_occupancy_calculations(self) -> None:
        """Tests the occupancy metrics module using pandas dataframe directly."""
        df_records = []
        for occ in self.occupancy_data:
            rec = occ.__dict__.copy()
            rec.pop("_sa_instance_state", None)
            df_records.append(rec)
        
        df = pd.DataFrame(df_records)
        df["collected_at"] = pd.to_datetime(df["collected_at"])

        # Current Occupancy
        current = calculate_current_occupancy(df)
        self.assertIsNotNone(current)
        self.assertEqual(current["occupied_slots"], 80)
        self.assertEqual(current["occupancy_percentage"], 80.0)

        # Occupancy Metrics
        metrics = calculate_occupancy_metrics(df)
        self.assertEqual(metrics["average_occupancy"], 50.0)
        self.assertEqual(metrics["maximum_occupancy"], 80.0)
        self.assertEqual(metrics["minimum_occupancy"], 20.0)
        self.assertEqual(metrics["occupancy_percentage"], 50.0)

        # Utilization Metrics
        util = calculate_utilization_metrics(df)
        self.assertEqual(util["facility_utilization"], 50.0)
        self.assertEqual(util["average_occupied_slots"], 50.0)
        self.assertEqual(util["average_available_slots"], 50.0)
        self.assertEqual(util["slot_utilization"], 50.0)

    def test_02_session_statistics(self) -> None:
        """Tests the session metrics module."""
        df_records = []
        for sess in self.session_data:
            rec = sess.__dict__.copy()
            rec.pop("_sa_instance_state", None)
            df_records.append(rec)
        
        df = pd.DataFrame(df_records)
        df["check_in_time"] = pd.to_datetime(df["check_in_time"])

        metrics = calculate_session_metrics(df)
        self.assertEqual(metrics["session_count"], 2)
        self.assertEqual(metrics["average_duration"], 90.0)
        self.assertEqual(metrics["median_duration"], 90.0)
        self.assertEqual(metrics["minimum_duration"], 60.0)
        self.assertEqual(metrics["maximum_duration"], 120.0)
        self.assertEqual(metrics["duration_distribution"]["1h-2h"], 1)
        self.assertEqual(metrics["duration_distribution"]["2h-4h"], 1)

    def test_03_reservation_analytics(self) -> None:
        """Tests the reservation metrics module."""
        df_records = []
        for res in self.reservation_data:
            rec = res.__dict__.copy()
            rec.pop("_sa_instance_state", None)
            df_records.append(rec)
        
        df = pd.DataFrame(df_records)
        df["reservation_start"] = pd.to_datetime(df["reservation_start"])

        metrics = calculate_reservation_metrics(df)
        self.assertEqual(metrics["total_reservations"], 2)
        self.assertEqual(metrics["reservation_success_rate"], 50.0)
        self.assertEqual(metrics["cancellation_rate"], 50.0)
        self.assertEqual(metrics["average_reservation_duration"], 60.0)

    def test_04_peak_hour_detection(self) -> None:
        """Tests peak hour rankings detection."""
        df_records = []
        for occ in self.occupancy_data:
            rec = occ.__dict__.copy()
            rec.pop("_sa_instance_state", None)
            df_records.append(rec)
        
        df = pd.DataFrame(df_records)
        df["collected_at"] = pd.to_datetime(df["collected_at"])

        peak_info = detect_peak_hours(df)
        self.assertTrue(len(peak_info["peak_hours"]) > 0)
        self.assertTrue(len(peak_info["least_busy_hours"]) > 0)
        self.assertIsNotNone(peak_info["busiest_day"])

    async def test_05_api_endpoints_populated(self) -> None:
        """Verifies API router responses with populated database records."""
        await self._insert_test_data()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # Overview
            res = await ac.get(f"/analytics/overview?facility_id={self.facility_id}")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["facility_id"], self.facility_id)
            self.assertEqual(data["average_occupancy"], 50.0)
            self.assertEqual(data["reservation_count"], 2)

            # Occupancy
            res = await ac.get(f"/analytics/occupancy?facility_id={self.facility_id}")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["occupancy_percentage"], 50.0)
            self.assertTrue(len(data["hourly_trend"]) > 0)

            # Utilization
            res = await ac.get(f"/analytics/utilization?facility_id={self.facility_id}")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["facility_utilization"], 50.0)

            # Reservations
            res = await ac.get(f"/analytics/reservations?facility_id={self.facility_id}")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["total_reservations"], 2)
            self.assertEqual(data["reservation_success_rate"], 50.0)

            # Sessions
            res = await ac.get(f"/analytics/sessions?facility_id={self.facility_id}")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["session_count"], 2)
            self.assertEqual(data["average_duration"], 90.0)

            # Peak Hours
            res = await ac.get(f"/analytics/peak-hours?facility_id={self.facility_id}")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertTrue(len(data["peak_hours"]) > 0)

            # Trends
            res = await ac.get(f"/analytics/trends?facility_id={self.facility_id}")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertTrue(len(data["rolling_average"]) > 0)

            # Daily Report
            res = await ac.get(f"/analytics/daily?facility_id={self.facility_id}&date={self.now.date().isoformat()}")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["report_type"], "DAILY")
            self.assertEqual(data["period"], self.now.date().isoformat())

            # Weekly Report
            start_date = (self.now.date() - timedelta(days=2)).isoformat()
            end_date = self.now.date().isoformat()
            res = await ac.get(f"/analytics/weekly?facility_id={self.facility_id}&start_date={start_date}&end_date={end_date}")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["report_type"], "WEEKLY")

            # Monthly Report
            res = await ac.get(f"/analytics/monthly?facility_id={self.facility_id}&year={self.now.year}&month={self.now.month}")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["report_type"], "MONTHLY")

    async def test_06_api_error_handling(self) -> None:
        """Validates error cases such as non-existent facility, empty dataset, and invalid range."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Non-existent facility
            res = await ac.get("/analytics/overview?facility_id=MISSING-FAC-ID")
            self.assertEqual(res.status_code, 404)
            data = res.json()
            self.assertEqual(data["error"]["code"], "MISSING_FACILITY")

            # Insert data to activate facility
            await self._insert_test_data()

            # 2. Empty dataset for valid facility because date range is way in the future
            future_start = (self.now + timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
            future_end = (self.now + timedelta(days=15)).strftime("%Y-%m-%dT%H:%M:%SZ")
            res = await ac.get(f"/analytics/occupancy?facility_id={self.facility_id}&start_date={future_start}&end_date={future_end}")
            self.assertEqual(res.status_code, 404)
            data = res.json()
            self.assertEqual(data["error"]["code"], "EMPTY_DATASET")

            # 3. Invalid date range (start after end)
            res = await ac.get(f"/analytics/occupancy?facility_id={self.facility_id}&start_date={future_end}&end_date={future_start}")
            self.assertEqual(res.status_code, 400)
            data = res.json()
            self.assertEqual(data["error"]["code"], "INVALID_DATE_RANGE")



if __name__ == "__main__":
    unittest.main()
