import os
import shutil
import unittest
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from ai_service.main import app
from ai_service.database.session import get_db_session
from ai_service.database.base import Base
from ai_service.models.occupancy import OccupancyHistory
from ai_service.models.reservation import ReservationHistory
from ai_service.models.session import ParkingSessionHistory

from ai_service.ml.metrics import calculate_mape, evaluate_predictions
from ai_service.ml.model_selector import select_best_model
from ai_service.ml.persistence import save_forecasting_package, load_forecasting_package
from ai_service.ml.forecasting import OccupancyForecaster

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


class TestOccupancyForecasting(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.test_dir = "./test_forecasting_dir"
        self.model_file = os.path.join(self.test_dir, "occupancy_forecast_test.joblib")
        os.makedirs(self.test_dir, exist_ok=True)
        app.dependency_overrides[get_db_session] = override_get_db_session

    async def asyncTearDown(self) -> None:
        async with engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine_test.dispose()
        app.dependency_overrides.clear()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_metrics_calculation(self):
        """Tests the custom MAPE and general evaluation metrics calculators."""
        y_true = np.array([50.0, 60.0, 70.0])
        y_pred = np.array([48.0, 63.0, 70.0])
        
        # Hand-calculation for MAPE: (|2/50| + |3/60| + |0/70|)/3 = (0.04 + 0.05 + 0.0)/3 = 0.03 = 3.0%
        mape = calculate_mape(y_true, y_pred)
        self.assertAlmostEqual(mape, 3.0)

        metrics = evaluate_predictions(y_true, y_pred)
        self.assertEqual(metrics["mae"], 1.6666666666666667)
        self.assertAlmostEqual(metrics["mape"], 3.0)
        self.assertGreater(metrics["confidence"], 90.0)

    def test_model_selection(self):
        """Tests training multiple regressors on mock features and selecting the best."""
        np.random.seed(42)
        X = pd.DataFrame(np.random.rand(50, 5), columns=[f"feat_{i}" for i in range(5)])
        y = pd.Series(np.random.rand(50) * 100.0)

        best_model, best_name, all_metrics, best_metrics = select_best_model(X, y)
        self.assertIsNotNone(best_model)
        self.assertIn(best_name, all_metrics)
        self.assertIn("rmse", best_metrics)

    def test_model_persistence(self):
        """Tests model package saving and loading processes."""
        mock_package = {
            "models": {"15": "mock_model_15"},
            "features": {"15": ["feat_1", "feat_2"]},
            "metrics": {"15": {"rmse": 1.2, "confidence": 98.0}},
            "best_model_names": {"15": "Linear Regression"}
        }
        
        save_forecasting_package(mock_package, self.model_file)
        self.assertTrue(os.path.exists(self.model_file))
        
        loaded = load_forecasting_package(self.model_file)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["best_model_names"]["15"], "Linear Regression")

    async def _populate_dummy_db_records(self, session: AsyncSession):
        """Helper to load dummy history rows into the database."""
        now = datetime.now(timezone.utc)
        # Populate 30 records at 15-minute intervals to allow rolling features to generate without NaN
        for i in range(35):
            collected_time = now - timedelta(minutes=15 * (35 - i))
            occ = OccupancyHistory(
                facility_id=1,
                zone_id="ZONE-A",
                total_slots=100,
                occupied_slots=40 + (i % 8),
                available_slots=60 - (i % 8),
                occupancy_percentage=40.0 + (i % 8),
                collected_at=collected_time
            )
            session.add(occ)

        # Populate a few reservation and session records
        for i in range(12):
            res_time = now - timedelta(hours=i)
            res = ReservationHistory(
                reservation_id=f"RES-TST-{i}",
                facility_id=1,
                slot_id=f"SLOT-{i}",
                reservation_status="COMPLETED",
                reservation_start=res_time - timedelta(hours=1),
                reservation_end=res_time,
                duration_minutes=60.0,
                collected_at=res_time
            )
            session.add(res)

            sess = ParkingSessionHistory(
                session_id=f"SESS-TST-{i}",
                facility_id=1,
                vehicle_type="CAR",
                check_in_time=res_time - timedelta(hours=2),
                check_out_time=res_time,
                duration_minutes=120.0,
                parking_fee=12.0,
                collected_at=res_time
            )
            session.add(sess)

        await session.commit()

    async def test_forecasting_pipeline_and_api(self):
        """Verifies full training, status check, metrics retrieval, and prediction APIs."""
        async with AsyncSessionLocalTest() as session:
            await self._populate_dummy_db_records(session)

        # Create forecaster pointing to our temporary model file path
        forecaster = OccupancyForecaster(model_path=self.model_file)
        
        # Temporarily inject this forecaster instance into the forecasting_service
        from ai_service.services.forecasting_service import forecasting_service, ForecastingService
        from ai_service.api.deps import get_forecasting_service
        
        test_service = ForecastingService(forecaster=forecaster)
        app.dependency_overrides[get_forecasting_service] = lambda: test_service
        original_forecaster = forecasting_service.forecaster
        forecasting_service.forecaster = forecaster

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                # 1. Check status (should be NOT_TRAINED)
                resp = await ac.get("/forecast/status")
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp.json()["status"], "NOT_TRAINED")

                # 2. Check metrics (should return 404 since no models trained)
                resp = await ac.get("/forecast/metrics")
                self.assertEqual(resp.status_code, 404)

                # 3. Train models
                resp = await ac.post(f"/forecast/train?export_path={self.test_dir}")
                self.assertEqual(resp.status_code, 200, resp.text)
                train_data = resp.json()
                self.assertIn("message", train_data)
                self.assertIn("horizons", train_data)

                # 4. Check status again (should be READY)
                resp = await ac.get("/forecast/status")
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp.json()["status"], "READY")

                # 5. Check metrics again (should be 200)
                resp = await ac.get("/forecast/metrics")
                self.assertEqual(resp.status_code, 200)
                metrics_data = resp.json()
                self.assertIn("15", metrics_data["metrics"])

                # 6. Retrieve 15-minute prediction
                resp = await ac.get("/forecast/15?facility_id=1")
                self.assertEqual(resp.status_code, 200, resp.text)
                pred_data = resp.json()
                self.assertEqual(pred_data["facility_id"], 1)
                self.assertIn("current_occupancy", pred_data)
                self.assertIn("prediction_15", pred_data)
                self.assertIn("confidence", pred_data)

                # 7. Custom forecast prediction for 45 minutes (triggers dynamic training)
                custom_req = {"facility_id": 1, "target_minutes": 45}
                resp = await ac.post(f"/forecast/custom?export_path={self.test_dir}", json=custom_req)
                self.assertEqual(resp.status_code, 200, resp.text)
                custom_data = resp.json()
                self.assertEqual(custom_data["facility_id"], 1)
                self.assertIn("prediction_custom", custom_data)
                self.assertIn("confidence", custom_data)

        finally:
            forecasting_service.forecaster = original_forecaster
            if get_forecasting_service in app.dependency_overrides:
                del app.dependency_overrides[get_forecasting_service]
