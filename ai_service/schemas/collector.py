"""
Pydantic schemas for Data Collector status, manual triggers, and dataset export summaries.
"""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class CollectionSummary(BaseModel):
    """
    Summary returned after a single collector execution cycle.
    """

    collector_name: str = Field(..., description="Name of the collector")
    status: str = Field(..., description="Execution status (SUCCESS, WARNING, ERROR)")
    fetched_count: int = Field(default=0, description="Total records retrieved from backend API")
    inserted_count: int = Field(default=0, description="New records stored in database")
    duplicate_count: int = Field(default=0, description="Duplicate records ignored")
    errors_count: int = Field(default=0, description="Number of items failing validation or storage")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Cycle execution timestamp")
    message: str = Field(default="", description="Summary message or error detail")


class CollectorStatusResponse(BaseModel):
    """
    Response schema for GET /collector/status endpoint.
    """

    scheduler_status: str = Field(..., description="Current status of APScheduler (running/stopped)")
    last_collection_time: Optional[datetime] = Field(default=None, description="Most recent collection timestamp")
    total_records: Dict[str, int] = Field(
        ...,
        description="Total row count for each historical table in the database",
        example={"occupancy": 1500, "reservations": 450, "sessions": 890},
    )
    last_summaries: Dict[str, CollectionSummary] = Field(
        default={},
        description="Last collection summary for each data collector",
    )


class ExportSummaryResponse(BaseModel):
    """
    Response schema for GET /collector/export endpoint.
    """

    status: str = Field(..., description="Export status (SUCCESS / ERROR)")
    exported_at: datetime = Field(default_factory=datetime.utcnow)
    export_directory: str = Field(..., description="Path where CSV files are saved")
    exported_files: List[str] = Field(..., description="List of generated CSV file paths")
    records_exported: Dict[str, int] = Field(..., description="Record count exported per dataset")
