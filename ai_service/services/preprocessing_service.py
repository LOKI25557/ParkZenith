"""
Preprocessing Service module for ParkZenith Preprocessing Pipeline.
Provides high-level orchestration, state management, statistical summaries, and info utilities.
"""

import os
from datetime import datetime, timezone
import logging
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from ai_service.config.settings import settings
from ai_service.repositories.occupancy_repository import OccupancyRepository
from ai_service.repositories.reservation_repository import ReservationRepository
from ai_service.repositories.session_repository import ParkingSessionRepository
from ai_service.preprocessing.dataset_builder import DatasetBuilder

logger = logging.getLogger(__name__)


class PreprocessingService:
    """
    Manages coordination of cleaning, validation, feature engineering, and exports.
    Keeps API controllers thin and clean.
    """

    def __init__(self, export_dir: str = settings.EXPORT_PATH) -> None:
        self.export_dir = os.path.abspath(export_dir)
        self.dataset_builder = DatasetBuilder(export_dir=self.export_dir)
        
        # State variables for run tracing
        self._last_run_timestamp: Optional[datetime] = None
        self._last_run_status: str = "PENDING"
        self._last_run_metrics: Dict[str, Any] = {}

    def get_last_run_details(self) -> Dict[str, Any]:
        """Returns details of the last execution."""
        return {
            "last_run_at": self._last_run_timestamp.isoformat() if self._last_run_timestamp else None,
            "last_run_status": self._last_run_status,
            "last_run_metrics": self._last_run_metrics,
        }

    async def get_pipeline_status(self, session: AsyncSession) -> Dict[str, Any]:
        """
        Retrieves the current status of the database and historical datasets.
        """
        occ_repo = OccupancyRepository(session)
        res_repo = ReservationRepository(session)
        sess_repo = ParkingSessionRepository(session)

        try:
            occ_count = await occ_repo.count()
            res_count = await res_repo.count()
            sess_count = await sess_repo.count()
        except Exception as exc:
            logger.error("Failed to query DB counts: %s", str(exc))
            occ_count = res_count = sess_count = 0

        # Check if datasets directory contains exported CSVs
        has_exports = False
        files = ["occupancy_training.csv", "reservation_training.csv", "session_training.csv", "forecast_training.csv"]
        missing_files = []
        for f in files:
            p = os.path.join(self.export_dir, f)
            if os.path.exists(p):
                has_exports = True
            else:
                missing_files.append(f)

        return {
            "status": "READY" if (occ_count > 0 or res_count > 0 or sess_count > 0) else "NO_DATA",
            "export_directory": self.export_dir,
            "database_records": {
                "occupancy": occ_count,
                "reservations": res_count,
                "sessions": sess_count,
            },
            "exported_datasets_found": has_exports and len(missing_files) == 0,
            "missing_exported_files": missing_files,
            "last_execution": self.get_last_run_details(),
        }

    async def run_pipeline(self, session: AsyncSession, export_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Coordinates running the entire cleaning, validation, feature engineering, and scaling pipeline.
        Saves resulting DataFrames to disk.
        """
        logger.info("Starting preprocessing service pipeline run...")
        self._last_run_status = "RUNNING"
        
        try:
            results = await self.dataset_builder.build_and_export_datasets(session, export_path=export_path)
            
            # Update internal state on success
            self._last_run_timestamp = datetime.now(timezone.utc)
            self._last_run_status = "SUCCESS"
            self._last_run_metrics = {
                "exported_files": list(results["exported_files"].keys()),
                "record_counts": results["record_counts"],
                "pipeline_metrics": results["pipeline_metrics"],
            }
            return results
        except Exception as exc:
            logger.exception("Error executing preprocessing service run.")
            self._last_run_status = "FAILED"
            self._last_run_metrics = {"error": str(exc)}
            raise

    async def get_features_summary(self, session: AsyncSession) -> Dict[str, Any]:
        """
        Runs the feature engineering pipeline and computes summaries (mean, std, min, max, count, null_count)
        for all generated features without writing them to disk.
        """
        # Load raw data
        raw_occ, raw_res, raw_sess = await self.dataset_builder.load_raw_data(session)

        if len(raw_occ) == 0 and len(raw_res) == 0 and len(raw_sess) == 0:
            return {
                "status": "EMPTY",
                "summary": "No data available to summarize."
            }

        # Run preprocessing pipeline (no export)
        occ_train, res_train, sess_train, forecast_train, _ = self.dataset_builder.pipeline.run(
            raw_occupancy=raw_occ,
            raw_reservation=raw_res,
            raw_session=raw_sess
        )

        def make_df_summary(df: pd.DataFrame) -> Dict[str, Any]:
            if len(df) == 0:
                return {"row_count": 0, "columns": []}
            
            # Select numerical types
            num_df = df.select_dtypes(include=[np.number])
            stats = num_df.describe().to_dict()
            
            # Add missing count/ratio to stats
            summary_dict = {}
            for col, col_stats in stats.items():
                col_stats["null_count"] = int(df[col].isnull().sum())
                col_stats["null_percentage"] = float(col_stats["null_count"] / len(df) * 100.0)
                summary_dict[col] = col_stats

            return {
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": list(df.columns),
                "numerical_features_summary": summary_dict
            }

        return {
            "status": "SUCCESS",
            "summaries": {
                "occupancy_training": make_df_summary(occ_train),
                "reservation_training": make_df_summary(res_train),
                "session_training": make_df_summary(sess_train),
                "forecast_training": make_df_summary(forecast_train),
            }
        }

    def get_datasets_info(self, export_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Scans exported CSV datasets to compile file size, column list, row count, and creation metrics.
        """
        target_dir = os.path.abspath(export_path) if export_path else self.export_dir
        
        files = {
            "occupancy_training": "occupancy_training.csv",
            "reservation_training": "reservation_training.csv",
            "session_training": "session_training.csv",
            "forecast_training": "forecast_training.csv",
        }

        info_dict = {}
        for key, fname in files.items():
            fpath = os.path.join(target_dir, fname)
            if not os.path.exists(fpath):
                info_dict[key] = {"exists": False, "file_name": fname}
                continue

            try:
                # Load first few lines to get columns without keeping file handles open
                with open(fpath, "r", encoding="utf-8") as f:
                    sample_df = pd.read_csv(f, nrows=5)
                    cols = list(sample_df.columns)
                
                # Load entire file to get exact row count
                with open(fpath, "r", encoding="utf-8") as f:
                    full_df = pd.read_csv(f)
                    row_count = len(full_df)

                stat = os.stat(fpath)
                info_dict[key] = {
                    "exists": True,
                    "file_name": fname,
                    "file_path": fpath,
                    "file_size_bytes": stat.st_size,
                    "last_modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    "row_count": row_count,
                    "columns": cols,
                    "column_count": len(cols)
                }
            except Exception as exc:
                logger.error("Failed to read dataset info for %s: %s", fname, str(exc))
                info_dict[key] = {
                    "exists": True,
                    "file_name": fname,
                    "error": f"Failed to read file: {str(exc)}"
                }

        return {
            "export_directory": target_dir,
            "datasets": info_dict
        }
