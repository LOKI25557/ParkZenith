"""
Verification tests for Feature Engineering & Data Preprocessing Pipeline.
"""

import os
import shutil
import unittest
from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from ai_service.main import app
from ai_service.config.settings import settings
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from ai_service.database.session import get_db_session
from ai_service.database.base import Base
from ai_service.models.occupancy import OccupancyHistory
from ai_service.models.reservation import ReservationHistory
from ai_service.models.session import ParkingSessionHistory

# Import components to test
from ai_service.preprocessing.cleaning import (
    remove_duplicates,
    handle_missing_values,
    validate_timestamps,
    remove_invalid_records,
    handle_null_occupancy,
    handle_invalid_reservation_durations,
    handle_invalid_parking_sessions,
    remove_outliers,
)
from ai_service.preprocessing.validation import (
    validate_occupancy_schema,
    validate_reservation_schema,
    validate_session_schema,
)
from ai_service.preprocessing.normalization import ScalerWrapper
from ai_service.preprocessing.encoding import CategoricalEncoder
from ai_service.features.time_features import generate_time_features
from ai_service.features.occupancy_features import generate_occupancy_features
from ai_service.features.reservation_features import (
    generate_reservation_transaction_features,
    aggregate_reservation_features_hourly,
)
from ai_service.features.session_features import (
    generate_session_transaction_features,
    aggregate_session_features_hourly,
)
from ai_service.preprocessing.pipeline import PreprocessingPipeline
from ai_service.preprocessing.dataset_builder import DatasetBuilder


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


class TestPreprocessingPipeline(unittest.IsolatedAsyncioTestCase):
    """
    Test suite verifying cleaning, normalization, encoding, feature engineering, and route logic.
    """

    async def asyncSetUp(self) -> None:
        """Sets up tables and sample records."""
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        app.dependency_overrides[get_db_session] = override_get_db_session

        self.test_dir = "./test_run_datasets"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)
        os.makedirs(self.test_dir, exist_ok=True)

        self.now = datetime.now(timezone.utc).replace(minute=45, second=0, microsecond=0)
        self.facility_id = "FAC-PREP-001"

        # Populate DB tables with basic cleanable records
        async with AsyncSessionLocalTest() as session:
            # 1. Occupancy records
            occ_list = [
                OccupancyHistory(
                    facility_id=self.facility_id,
                    zone_id="ZONE-X",
                    total_slots=100,
                    occupied_slots=25,
                    available_slots=75,
                    occupancy_percentage=25.0,
                    collected_at=self.now - timedelta(hours=3),
                ),
                OccupancyHistory(
                    facility_id=self.facility_id,
                    zone_id="ZONE-X",
                    total_slots=100,
                    occupied_slots=35,
                    available_slots=65,
                    occupancy_percentage=35.0,
                    collected_at=self.now - timedelta(hours=2),
                ),
                OccupancyHistory(
                    facility_id=self.facility_id,
                    zone_id="ZONE-X",
                    total_slots=100,
                    occupied_slots=45,
                    available_slots=55,
                    occupancy_percentage=45.0,
                    collected_at=self.now - timedelta(hours=1),
                ),
            ]
            session.add_all(occ_list)

            # 2. Reservation records
            res_list = [
                ReservationHistory(
                    reservation_id="RES-P01",
                    facility_id=self.facility_id,
                    slot_id="SLOT-P1",
                    reservation_status="COMPLETED",
                    reservation_start=self.now - timedelta(hours=3),
                    reservation_end=self.now - timedelta(hours=2),
                    duration_minutes=60.0,
                    collected_at=self.now - timedelta(hours=3),
                ),
                ReservationHistory(
                    reservation_id="RES-P02",
                    facility_id=self.facility_id,
                    slot_id="SLOT-P2",
                    reservation_status="CANCELLED",
                    reservation_start=self.now - timedelta(hours=1),
                    reservation_end=self.now,
                    duration_minutes=60.0,
                    collected_at=self.now - timedelta(hours=1),
                ),
            ]
            session.add_all(res_list)

            # 3. Session records
            sess_list = [
                ParkingSessionHistory(
                    session_id="SESS-P01",
                    facility_id=self.facility_id,
                    vehicle_type="CAR",
                    check_in_time=self.now - timedelta(hours=3),
                    check_out_time=self.now - timedelta(hours=1),
                    duration_minutes=120.0,
                    parking_fee=10.0,
                    collected_at=self.now - timedelta(hours=3),
                ),
                # Active session
                ParkingSessionHistory(
                    session_id="SESS-P02",
                    facility_id=self.facility_id,
                    vehicle_type="EV",
                    check_in_time=self.now - timedelta(minutes=30),
                    check_out_time=None,
                    duration_minutes=None,
                    parking_fee=None,
                    collected_at=self.now - timedelta(minutes=30),
                ),
            ]
            session.add_all(sess_list)

            await session.commit()

    async def asyncTearDown(self) -> None:
        """Removes tables and test directories."""
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine_test.dispose()
        app.dependency_overrides.clear()
        
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_cleaning_functions(self):
        """Verifies individual data cleaning functions."""
        # 1. Duplicates
        df_dup = pd.DataFrame({"id": [1, 1, 2], "val": ["a", "a", "b"]})
        df_clean_dup = remove_duplicates(df_dup)
        self.assertEqual(len(df_clean_dup), 2)

        # 2. Missing values
        df_miss = pd.DataFrame({"id": [1, 2, 3], "val": [10.0, np.nan, 20.0]})
        df_fill_mean = handle_missing_values(df_miss, strategy="mean", columns=["val"])
        self.assertEqual(df_fill_mean.loc[1, "val"], 15.0)

        # 3. Timestamps validation
        future_time = datetime.now(timezone.utc) + timedelta(days=10)
        df_time = pd.DataFrame({"time": [self.now, pd.NaT, future_time]})
        df_time_clean = validate_timestamps(df_time, timestamp_cols=["time"])
        self.assertEqual(len(df_time_clean), 1)  # Drops NaT and future timestamp

        # 4. Null occupancy
        df_occ = pd.DataFrame({
            "total_slots": [100, 100, 0],
            "occupied_slots": [120, np.nan, 5],
            "occupancy_percentage": [120.0, 50.0, 50.0]
        })
        df_occ_clean = handle_null_occupancy(df_occ)
        # Drop total_slots <= 0 (row 2) -> len is 2
        self.assertEqual(len(df_occ_clean), 2)
        # Clamped occupied slots to total slots
        self.assertEqual(df_occ_clean.iloc[0]["occupied_slots"], 100)
        # Calculated occupied slots from percentage for row 1 (100 * 50% = 50)
        self.assertEqual(df_occ_clean.iloc[1]["occupied_slots"], 50)

        # 5. Invalid reservation duration
        df_res = pd.DataFrame({
            "reservation_start": [self.now, self.now],
            "reservation_end": [self.now + timedelta(minutes=45), self.now - timedelta(minutes=45)],
            "duration_minutes": [np.nan, 45]
        })
        df_res_clean = handle_invalid_reservation_durations(df_res)
        # Drops row where start > end -> len is 1
        self.assertEqual(len(df_res_clean), 1)
        # Recomputed missing duration
        self.assertEqual(df_res_clean.iloc[0]["duration_minutes"], 45.0)

        # 6. Outliers
        df_outliers = pd.DataFrame({"val": [1.0, 2.0, 1.5, 100.0]})
        df_no_outliers = remove_outliers(df_outliers, columns=["val"], threshold=1.5)
        self.assertEqual(len(df_no_outliers), 3)

    def test_02_validation_schemas(self):
        """Verifies structural and rule validators."""
        # Occupancy
        df_occ_ok = pd.DataFrame({
            "facility_id": ["FAC"],
            "total_slots": [10],
            "occupied_slots": [2],
            "occupancy_percentage": [20.0],
            "collected_at": [self.now],
        })
        report = validate_occupancy_schema(df_occ_ok)
        self.assertTrue(report["valid"])

        # Reservation invalid
        df_res_bad = pd.DataFrame({
            "reservation_id": ["RES"],
            "facility_id": ["FAC"],
            "slot_id": ["SLOT"],
            "reservation_status": ["COMPLETED"],
            "reservation_start": [self.now],
            "reservation_end": [self.now - timedelta(hours=1)],
            "duration_minutes": [-10],
            "collected_at": [self.now],
        })
        report = validate_reservation_schema(df_res_bad)
        self.assertFalse(report["valid"])

    def test_03_normalization_and_encoding(self):
        """Verifies scikit-learn scaling wrappers and encoders."""
        # 1. Normalization
        df = pd.DataFrame({"num": [10.0, 20.0, 30.0]})
        scaler = ScalerWrapper(strategy="minmax")
        scaled_df = scaler.fit_transform(df, ["num"])
        self.assertAlmostEqual(scaled_df.loc[0, "num"], 0.0)
        self.assertAlmostEqual(scaled_df.loc[2, "num"], 1.0)

        # 2. Categorical encoding
        df_cat = pd.DataFrame({"cat": ["A", "B", "A", "C"]})
        encoder = CategoricalEncoder(strategy="onehot")
        encoded_df = encoder.fit_transform(df_cat, ["cat"])
        self.assertIn("cat_A", encoded_df.columns)
        self.assertIn("cat_B", encoded_df.columns)
        self.assertIn("cat_C", encoded_df.columns)
        self.assertEqual(encoded_df.loc[0, "cat_A"], 1.0)

    def test_04_feature_generation(self):
        """Verifies timeseries, occupancy, reservation, and session features."""
        # Time features
        df_t = pd.DataFrame({"time": [pd.Timestamp("2026-07-29 10:00:00+00:00")]})
        df_t_feats = generate_time_features(df_t, "time")
        self.assertEqual(df_t_feats.loc[0, "time_hour"], 10)
        self.assertEqual(df_t_feats.loc[0, "time_dayofweek"], 2)  # Wednesday
        self.assertEqual(df_t_feats.loc[0, "time_is_weekend"], 0)

        # Occupancy features
        df_occ = pd.DataFrame({
            "facility_id": ["FAC", "FAC", "FAC"],
            "collected_at": [self.now - timedelta(hours=2), self.now - timedelta(hours=1), self.now],
            "total_slots": [100, 100, 100],
            "occupied_slots": [10, 20, 30],
            "occupancy_percentage": [10.0, 20.0, 30.0],
        })
        df_occ_feats = generate_occupancy_features(df_occ)
        self.assertEqual(df_occ_feats.iloc[2]["occupancy_diff"], 10.0)
        self.assertEqual(df_occ_feats.iloc[2]["occupancy_lag_1"], 20.0)

        # Reservation hourly aggregation
        df_res = pd.DataFrame({
            "facility_id": ["FAC", "FAC"],
            "reservation_start": [self.now - timedelta(minutes=30), self.now - timedelta(minutes=15)],
            "duration_minutes": [30.0, 45.0],
            "reservation_status": ["COMPLETED", "CANCELLED"]
        })
        df_res_agg = aggregate_reservation_features_hourly(df_res, total_slots_default=10)
        self.assertGreater(len(df_res_agg), 0)
        self.assertEqual(df_res_agg.iloc[0]["cancellation_rate"], 0.5)

        # Session hourly aggregation
        df_sess = pd.DataFrame({
            "facility_id": ["FAC", "FAC"],
            "check_in_time": [self.now - timedelta(minutes=40), self.now - timedelta(minutes=10)],
            "check_out_time": [self.now - timedelta(minutes=20), pd.NaT],
            "duration_minutes": [20.0, np.nan],
            "parking_fee": [5.0, np.nan]
        })
        df_sess_agg = aggregate_session_features_hourly(df_sess, total_slots_default=10)
        self.assertGreater(len(df_sess_agg), 0)

    async def test_05_builder_and_service(self):
        """Verifies end-to-end dataset builder execution and exports."""
        async with AsyncSessionLocalTest() as session:
            builder = DatasetBuilder(export_dir=self.test_dir)
            results = await builder.build_and_export_datasets(session)

            self.assertEqual(results["status"], "SUCCESS")
            for key, path in results["exported_files"].items():
                self.assertTrue(os.path.exists(path))

    async def test_06_api_endpoints(self):
        """Verifies FastAPI controller routes respond with standard JSON structure."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            # 1. Pipeline status
            res_status = await client.get("/preprocessing/status")
            self.assertEqual(res_status.status_code, 200)
            data = res_status.json()
            self.assertEqual(data["status"], "READY")
            self.assertEqual(data["database_records"]["occupancy"], 3)

            # 2. Run pipeline
            res_run = await client.post(f"/preprocessing/run?export_path={self.test_dir}")
            self.assertEqual(res_run.status_code, 200)
            data_run = res_run.json()
            self.assertEqual(data_run["status"], "SUCCESS")

            # 3. Features summary
            res_sum = await client.get("/features/summary")
            self.assertEqual(res_sum.status_code, 200)
            data_sum = res_sum.json()
            self.assertEqual(data_sum["status"], "SUCCESS")

            # 4. Info
            res_info = await client.get(f"/datasets/info?export_path={self.test_dir}")
            self.assertEqual(res_info.status_code, 200)
            data_info = res_info.json()
            self.assertIn("forecast_training", data_info["datasets"])
            self.assertTrue(data_info["datasets"]["forecast_training"]["exists"])

            # 5. Export
            res_exp = await client.get(f"/datasets/export?export_path={self.test_dir}")
            self.assertEqual(res_exp.status_code, 200)
            data_exp = res_exp.json()
            self.assertEqual(data_exp["status"], "SUCCESS")
