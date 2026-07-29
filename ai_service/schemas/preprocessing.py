"""
Pydantic schemas for Preprocessing and Feature Engineering routes.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class DatabaseRecordsSummary(BaseModel):
    occupancy: int = Field(..., description="Count of historical occupancy records")
    reservations: int = Field(..., description="Count of historical reservation records")
    sessions: int = Field(..., description="Count of historical parking session records")


class LastExecutionDetails(BaseModel):
    last_run_at: Optional[str] = Field(None, description="ISO timestamp of the last execution")
    last_run_status: str = Field(..., description="Status of the last execution (e.g. SUCCESS, FAILED, PENDING)")
    last_run_metrics: Dict[str, Any] = Field(default_factory=dict, description="Execution metrics")


class PipelineStatusResponse(BaseModel):
    status: str = Field(..., description="Status of the pipeline ('READY' or 'NO_DATA')")
    export_directory: str = Field(..., description="Configured directory path for CSV exports")
    database_records: DatabaseRecordsSummary = Field(..., description="Summary of database records")
    exported_datasets_found: bool = Field(..., description="Whether all 4 expected training CSVs exist on disk")
    missing_exported_files: List[str] = Field(..., description="List of missing expected training CSV files")
    last_execution: LastExecutionDetails = Field(..., description="Details of the last pipeline execution")


class PipelineRunResponse(BaseModel):
    status: str = Field(..., description="Run status ('SUCCESS' or 'FAILED')")
    export_directory: str = Field(..., description="Target export directory")
    exported_files: Dict[str, str] = Field(..., description="Map of dataset name to exported CSV path")
    record_counts: Dict[str, int] = Field(..., description="Row counts for each exported dataset")
    pipeline_metrics: Dict[str, Any] = Field(..., description="Detailed metrics regarding duplicates, validation status, etc.")


class FeaturesSummaryResponse(BaseModel):
    status: str = Field(..., description="Status of the operation")
    summaries: Dict[str, Any] = Field(..., description="Detailed statistical summaries per training dataset")


class DatasetExportResponse(BaseModel):
    status: str = Field(..., description="Export status")
    export_directory: str = Field(..., description="Export target directory")
    exported_files: Dict[str, str] = Field(..., description="Map of dataset name to file path")
    record_counts: Dict[str, int] = Field(..., description="Number of records written per dataset")


class DatasetDetails(BaseModel):
    exists: bool = Field(..., description="Whether the file exists")
    file_name: str = Field(..., description="CSV filename")
    file_path: Optional[str] = Field(None, description="Absolute file path on disk")
    file_size_bytes: Optional[int] = Field(None, description="File size in bytes")
    last_modified: Optional[str] = Field(None, description="ISO timestamp of last modification time")
    row_count: Optional[int] = Field(None, description="Row count of the dataset")
    columns: Optional[List[str]] = Field(None, description="List of column names")
    column_count: Optional[int] = Field(None, description="Count of columns in dataset")
    error: Optional[str] = Field(None, description="Errors reading dataset file metadata")


class DatasetInfoResponse(BaseModel):
    export_directory: str = Field(..., description="Target directory scanned")
    datasets: Dict[str, DatasetDetails] = Field(..., description="Metadata maps for each of the training datasets")
