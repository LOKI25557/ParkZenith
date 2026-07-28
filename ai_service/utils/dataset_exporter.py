"""
Utility module for exporting historical database tables to CSV datasets using Pandas.
"""

import os
import logging
from typing import Dict, List, Any
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from ai_service.config.settings import settings
from ai_service.repositories.occupancy_repository import OccupancyRepository
from ai_service.repositories.reservation_repository import ReservationRepository
from ai_service.repositories.session_repository import ParkingSessionRepository
from ai_service.core.exceptions import CollectionError

logger = logging.getLogger(__name__)


class DatasetExporter:
    """
    Handles dumping database history records into Pandas DataFrames and exporting to CSV datasets.
    """

    def __init__(self, export_dir: str = settings.EXPORT_PATH) -> None:
        self.export_dir = os.path.abspath(export_dir)
        os.makedirs(self.export_dir, exist_ok=True)

    async def export_occupancy_history(self, session: AsyncSession) -> str:
        """
        Exports OccupancyHistory table to occupancy_history.csv.
        """
        repo = OccupancyRepository(session)
        records = await repo.get_all(limit=100000)

        data = [
            {
                "id": r.id,
                "facility_id": r.facility_id,
                "zone_id": r.zone_id,
                "total_slots": r.total_slots,
                "occupied_slots": r.occupied_slots,
                "available_slots": r.available_slots,
                "occupancy_percentage": r.occupancy_percentage,
                "collected_at": r.collected_at.isoformat() if r.collected_at else None,
            }
            for r in records
        ]

        df = pd.DataFrame(data)
        file_path = os.path.join(self.export_dir, "occupancy_history.csv")
        df.to_csv(file_path, index=False)
        logger.info("Exported %d occupancy records to %s", len(df), file_path)
        return file_path

    async def export_reservation_history(self, session: AsyncSession) -> str:
        """
        Exports ReservationHistory table to reservation_history.csv.
        """
        repo = ReservationRepository(session)
        records = await repo.get_all(limit=100000)

        data = [
            {
                "id": r.id,
                "reservation_id": r.reservation_id,
                "facility_id": r.facility_id,
                "slot_id": r.slot_id,
                "reservation_status": r.reservation_status,
                "reservation_start": r.reservation_start.isoformat() if r.reservation_start else None,
                "reservation_end": r.reservation_end.isoformat() if r.reservation_end else None,
                "duration_minutes": r.duration_minutes,
                "collected_at": r.collected_at.isoformat() if r.collected_at else None,
            }
            for r in records
        ]

        df = pd.DataFrame(data)
        file_path = os.path.join(self.export_dir, "reservation_history.csv")
        df.to_csv(file_path, index=False)
        logger.info("Exported %d reservation records to %s", len(df), file_path)
        return file_path

    async def export_parking_sessions(self, session: AsyncSession) -> str:
        """
        Exports ParkingSessionHistory table to parking_sessions.csv.
        """
        repo = ParkingSessionRepository(session)
        records = await repo.get_all(limit=100000)

        data = [
            {
                "id": r.id,
                "session_id": r.session_id,
                "facility_id": r.facility_id,
                "vehicle_type": r.vehicle_type,
                "check_in_time": r.check_in_time.isoformat() if r.check_in_time else None,
                "check_out_time": r.check_out_time.isoformat() if r.check_out_time else None,
                "duration_minutes": r.duration_minutes,
                "parking_fee": r.parking_fee,
                "collected_at": r.collected_at.isoformat() if r.collected_at else None,
            }
            for r in records
        ]

        df = pd.DataFrame(data)
        file_path = os.path.join(self.export_dir, "parking_sessions.csv")
        df.to_csv(file_path, index=False)
        logger.info("Exported %d parking session records to %s", len(df), file_path)
        return file_path

    async def export_all(self, session: AsyncSession) -> Dict[str, Any]:
        """
        Exports all history tables to CSV datasets.
        Returns detailed summary dictionary with file paths and record counts.
        """
        try:
            occ_path = await self.export_occupancy_history(session)
            res_path = await self.export_reservation_history(session)
            sess_path = await self.export_parking_sessions(session)

            occ_repo = OccupancyRepository(session)
            res_repo = ReservationRepository(session)
            sess_repo = ParkingSessionRepository(session)

            return {
                "status": "SUCCESS",
                "export_directory": self.export_dir,
                "exported_files": [occ_path, res_path, sess_path],
                "records_exported": {
                    "occupancy": await occ_repo.count(),
                    "reservations": await res_repo.count(),
                    "sessions": await sess_repo.count(),
                },
            }
        except Exception as exc:
            logger.exception("Failed to export dataset CSV files: %s", str(exc))
            raise CollectionError(
                message=f"Dataset export failed: {str(exc)}",
                details={"error": str(exc)},
            ) from exc
