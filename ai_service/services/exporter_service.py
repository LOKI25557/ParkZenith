"""
ExporterService module for coordinating dataset exports to CSV.
"""

import logging
from sqlalchemy.ext.asyncio import AsyncSession

from ai_service.utils.dataset_exporter import DatasetExporter
from ai_service.schemas.collector import ExportSummaryResponse

logger = logging.getLogger(__name__)


class ExporterService:
    """
    Service layer coordinating dataset CSV exports.
    """

    def __init__(self, exporter: DatasetExporter) -> None:
        self.exporter = exporter

    async def export_datasets(self, db_session: AsyncSession) -> ExportSummaryResponse:
        """
        Exports all database history tables to CSV files.
        """
        logger.info("Dataset export process initiated.")
        summary_dict = await self.exporter.export_all(db_session)
        logger.info("Dataset export completed successfully.")
        return ExportSummaryResponse(**summary_dict)
