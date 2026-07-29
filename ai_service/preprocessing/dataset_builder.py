"""
Dataset Builder module for ParkZenith Preprocessing Pipeline.
Handles database queries via repositories, triggers the pipeline, and saves training CSV datasets.
"""

import os
import logging
from typing import Dict, Any, Tuple
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from ai_service.config.settings import settings
from ai_service.repositories.occupancy_repository import OccupancyRepository
from ai_service.repositories.reservation_repository import ReservationRepository
from ai_service.repositories.session_repository import ParkingSessionRepository
from ai_service.preprocessing.pipeline import PreprocessingPipeline
from ai_service.core.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class DatasetBuilder:
    """
    Coordinates database queries, preprocessing pipeline runs, and output exports.
    """

    def __init__(self, export_dir: str = settings.EXPORT_PATH) -> None:
        self.export_dir = os.path.abspath(export_dir)
        os.makedirs(self.export_dir, exist_ok=True)
        self.pipeline = PreprocessingPipeline()

    async def load_raw_data(self, session: AsyncSession) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Loads raw historical records from database into Pandas DataFrames.
        """
        logger.info("Querying raw data from database...")
        
        # Limit set to 100000 to process large datasets efficiently without exhausting memory
        try:
            occ_repo = OccupancyRepository(session)
            occ_records = await occ_repo.get_all(limit=100000)
            
            res_repo = ReservationRepository(session)
            res_records = await res_repo.get_all(limit=100000)
            
            sess_repo = ParkingSessionRepository(session)
            sess_records = await sess_repo.get_all(limit=100000)
        except Exception as exc:
            logger.error("Failed to fetch records from database: %s", str(exc))
            raise DatabaseError(
                message=f"Database fetch failed: {str(exc)}",
                details={"error": str(exc)}
            ) from exc

        # Map occupancy history
        occ_data = [
            {
                "id": r.id,
                "facility_id": r.facility_id,
                "zone_id": r.zone_id,
                "total_slots": r.total_slots,
                "occupied_slots": r.occupied_slots,
                "available_slots": r.available_slots,
                "occupancy_percentage": r.occupancy_percentage,
                "collected_at": r.collected_at,
            }
            for r in occ_records
        ]
        occ_df = pd.DataFrame(occ_data)
        if len(occ_df) > 0:
            occ_df["collected_at"] = pd.to_datetime(occ_df["collected_at"], utc=True)

        # Map reservations history
        res_data = [
            {
                "id": r.id,
                "reservation_id": r.reservation_id,
                "facility_id": r.facility_id,
                "slot_id": r.slot_id,
                "reservation_status": r.reservation_status,
                "reservation_start": r.reservation_start,
                "reservation_end": r.reservation_end,
                "duration_minutes": r.duration_minutes,
                "collected_at": r.collected_at,
            }
            for r in res_records
        ]
        res_df = pd.DataFrame(res_data)
        if len(res_df) > 0:
            for col in ["reservation_start", "reservation_end", "collected_at"]:
                res_df[col] = pd.to_datetime(res_df[col], utc=True)

        # Map session history
        sess_data = [
            {
                "id": r.id,
                "session_id": r.session_id,
                "facility_id": r.facility_id,
                "vehicle_type": r.vehicle_type,
                "check_in_time": r.check_in_time,
                "check_out_time": r.check_out_time,
                "duration_minutes": r.duration_minutes,
                "parking_fee": r.parking_fee,
                "collected_at": r.collected_at,
            }
            for r in sess_records
        ]
        sess_df = pd.DataFrame(sess_data)
        if len(sess_df) > 0:
            for col in ["check_in_time", "check_out_time", "collected_at"]:
                sess_df[col] = pd.to_datetime(sess_df[col], utc=True)

        logger.info(
            "Raw data loaded: %d occupancy, %d reservations, %d sessions.",
            len(occ_df), len(res_df), len(sess_df)
        )
        return occ_df, res_df, sess_df

    async def build_and_export_datasets(self, session: AsyncSession, export_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Coordinates the whole load, clean, transform, and export cycle.
        """
        target_dir = os.path.abspath(export_path) if export_path else self.export_dir
        os.makedirs(target_dir, exist_ok=True)

        # 1. Load raw data
        raw_occ, raw_res, raw_sess = await self.load_raw_data(session)

        # Check for completely empty db
        if len(raw_occ) == 0 and len(raw_res) == 0 and len(raw_sess) == 0:
            logger.warning("All raw data tables are empty. Pipeline completed with empty exports.")
            
        # 2. Run preprocessing pipeline
        occ_train, res_train, sess_train, forecast_train, pipeline_metrics = self.pipeline.run(
            raw_occupancy=raw_occ,
            raw_reservation=raw_res,
            raw_session=raw_sess
        )

        # Define file paths
        occ_file = os.path.join(target_dir, "occupancy_training.csv")
        res_file = os.path.join(target_dir, "reservation_training.csv")
        sess_file = os.path.join(target_dir, "session_training.csv")
        forecast_file = os.path.join(target_dir, "forecast_training.csv")

        # Save to CSV
        occ_train.to_csv(occ_file, index=False)
        res_train.to_csv(res_file, index=False)
        sess_train.to_csv(sess_file, index=False)
        forecast_train.to_csv(forecast_file, index=False)

        logger.info("Exported training datasets to directory: %s", target_dir)

        return {
            "status": "SUCCESS",
            "export_directory": target_dir,
            "pipeline_metrics": pipeline_metrics,
            "exported_files": {
                "occupancy_training": occ_file,
                "reservation_training": res_file,
                "session_training": sess_file,
                "forecast_training": forecast_file,
            },
            "record_counts": {
                "occupancy_training": len(occ_train),
                "reservation_training": len(res_train),
                "session_training": len(sess_train),
                "forecast_training": len(forecast_train),
            }
        }
