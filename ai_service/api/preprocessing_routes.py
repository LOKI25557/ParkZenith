"""
FastAPI routing defining Preprocessing and Feature Engineering endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ai_service.api.deps import get_db_session, get_preprocessing_service
from ai_service.services.preprocessing_service import PreprocessingService
from ai_service.schemas.preprocessing import (
    PipelineStatusResponse,
    PipelineRunResponse,
    FeaturesSummaryResponse,
    DatasetExportResponse,
    DatasetInfoResponse,
)

# We use no common prefix or separate prefixes on router since the endpoints are spread across /preprocessing, /features, and /datasets
router = APIRouter()


@router.get(
    "/preprocessing/status",
    response_model=PipelineStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Pipeline Status",
    description="Returns database counts, exported file checks, and details of the last pipeline run.",
    tags=["Preprocessing Pipeline"],
)
async def get_preprocessing_status(
    preprocessing_service: PreprocessingService = Depends(get_preprocessing_service),
    db: AsyncSession = Depends(get_db_session),
) -> PipelineStatusResponse:
    """
    Retrieves current data pipeline readiness and run metrics.
    """
    res = await preprocessing_service.get_pipeline_status(db)
    return PipelineStatusResponse(**res)


@router.post(
    "/preprocessing/run",
    response_model=PipelineRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Run Preprocessing Pipeline",
    description="Loads raw data, executes cleaning, validation, feature engineering, scaling, encoding, and saves CSVs.",
    tags=["Preprocessing Pipeline"],
)
async def run_preprocessing_pipeline(
    export_path: Optional[str] = Query(None, description="Optional custom directory for dataset exports"),
    preprocessing_service: PreprocessingService = Depends(get_preprocessing_service),
    db: AsyncSession = Depends(get_db_session),
) -> PipelineRunResponse:
    """
    Triggers end-to-end data pipeline processing.
    """
    res = await preprocessing_service.run_pipeline(db, export_path=export_path)
    return PipelineRunResponse(**res)


@router.get(
    "/features/summary",
    response_model=FeaturesSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Features Summary Statistics",
    description="Runs preprocessing and feature engineering, then calculates mean, std, null ratios for all features.",
    tags=["Feature Engineering"],
)
async def get_features_summary(
    preprocessing_service: PreprocessingService = Depends(get_preprocessing_service),
    db: AsyncSession = Depends(get_db_session),
) -> FeaturesSummaryResponse:
    """
    Returns statistics (mean, std, missing ratio) for engineered features.
    """
    res = await preprocessing_service.get_features_summary(db)
    return FeaturesSummaryResponse(**res)


@router.get(
    "/datasets/export",
    response_model=DatasetExportResponse,
    status_code=status.HTTP_200_OK,
    summary="Export Latest Machine Learning Datasets",
    description="Triggers the pipeline and writes the latest cleaned and engineered features to disk.",
    tags=["Datasets Management"],
)
async def export_ml_datasets(
    export_path: Optional[str] = Query(None, description="Optional custom directory for dataset exports"),
    preprocessing_service: PreprocessingService = Depends(get_preprocessing_service),
    db: AsyncSession = Depends(get_db_session),
) -> DatasetExportResponse:
    """
    Executes the pipeline and writes the output files to disk.
    """
    res = await preprocessing_service.run_pipeline(db, export_path=export_path)
    # Map to export response format
    return DatasetExportResponse(
        status=res["status"],
        export_directory=res["export_directory"],
        exported_files=res["exported_files"],
        record_counts=res["record_counts"],
    )


@router.get(
    "/datasets/info",
    response_model=DatasetInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Dataset Metadata",
    description="Scans the export folder and details size, columns, row count, and modified dates of training files.",
    tags=["Datasets Management"],
)
async def get_datasets_info(
    export_path: Optional[str] = Query(None, description="Optional custom directory for dataset exports"),
    preprocessing_service: PreprocessingService = Depends(get_preprocessing_service),
) -> DatasetInfoResponse:
    """
    Scans generated training datasets and compiles metadata.
    """
    res = preprocessing_service.get_datasets_info(export_path=export_path)
    return DatasetInfoResponse(**res)
