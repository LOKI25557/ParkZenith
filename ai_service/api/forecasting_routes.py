"""
FastAPI router definition for Occupancy Forecasting API.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from ai_service.api.deps import get_db_session, get_forecasting_service
from ai_service.services.forecasting_service import ForecastingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/forecast", tags=["Occupancy Forecasting"])


class CustomForecastRequest(BaseModel):
    facility_id: int = Field(..., description="Identifier of the parking facility")
    target_minutes: int = Field(..., description="Forecast interval in minutes", gt=0)


class ForecastSnapshotResponse(BaseModel):
    facility_id: int
    current_occupancy: float = Field(..., description="Current occupancy percentage")
    prediction_15: float = Field(..., description="Predicted occupancy percentage in 15 minutes")
    prediction_30: float = Field(..., description="Predicted occupancy percentage in 30 minutes")
    prediction_60: float = Field(..., description="Predicted occupancy percentage in 60 minutes")
    confidence: float = Field(..., description="Model confidence score percentage")


class CustomForecastResponse(BaseModel):
    facility_id: int
    current_occupancy: float = Field(..., description="Current occupancy percentage")
    prediction_custom: float = Field(..., description="Predicted occupancy percentage at target interval")
    confidence: float = Field(..., description="Model confidence score percentage")


@router.post(
    "/train",
    status_code=status.HTTP_200_OK,
    summary="Train forecasting models",
    description="Loads datasets from Phase 3, runs model comparisons, selects the best regressor per horizon, and persists models.",
)
async def train_models(
    export_path: Optional[str] = Query(None, description="Custom dataset export directory path"),
    db: AsyncSession = Depends(get_db_session),
    service: ForecastingService = Depends(get_forecasting_service),
) -> Dict[str, Any]:
    """
    Triggers the training pipeline for 15, 30, and 60 minutes.
    """
    return await service.train_models(db, export_path)


@router.get(
    "/status",
    status_code=status.HTTP_200_OK,
    summary="Check model status",
    description="Indicates whether forecasting models have been successfully trained and loaded in memory.",
)
def get_model_status(
    service: ForecastingService = Depends(get_forecasting_service),
) -> Dict[str, Any]:
    """
    Returns forecaster training state status.
    """
    return service.get_status()


@router.get(
    "/metrics",
    status_code=status.HTTP_200_OK,
    summary="Get model metrics",
    description="Fetches performance metrics (MAE, RMSE, R2, MAPE, confidence) for each trained horizon.",
)
def get_model_metrics(
    service: ForecastingService = Depends(get_forecasting_service),
) -> Dict[str, Any]:
    """
    Returns the evaluation metrics of the best performing models.
    """
    return service.get_metrics()


@router.get(
    "/15",
    response_model=ForecastSnapshotResponse,
    status_code=status.HTTP_200_OK,
    summary="15-minute occupancy prediction",
    description="Generates future occupancy forecasts, using the 15-minute model confidence.",
)
async def get_forecast_15(
    facility_id: int = Query(..., description="Identifier of the parking facility"),
    db: AsyncSession = Depends(get_db_session),
    service: ForecastingService = Depends(get_forecasting_service),
) -> ForecastSnapshotResponse:
    """
    Generates 15-minute snapshot prediction.
    """
    res = await service.get_forecast_snapshot(db, facility_id, 15)
    return ForecastSnapshotResponse(**res)


@router.get(
    "/30",
    response_model=ForecastSnapshotResponse,
    status_code=status.HTTP_200_OK,
    summary="30-minute occupancy prediction",
    description="Generates future occupancy forecasts, using the 30-minute model confidence.",
)
async def get_forecast_30(
    facility_id: int = Query(..., description="Identifier of the parking facility"),
    db: AsyncSession = Depends(get_db_session),
    service: ForecastingService = Depends(get_forecasting_service),
) -> ForecastSnapshotResponse:
    """
    Generates 30-minute snapshot prediction.
    """
    res = await service.get_forecast_snapshot(db, facility_id, 30)
    return ForecastSnapshotResponse(**res)


@router.get(
    "/60",
    response_model=ForecastSnapshotResponse,
    status_code=status.HTTP_200_OK,
    summary="60-minute occupancy prediction",
    description="Generates future occupancy forecasts, using the 60-minute model confidence.",
)
async def get_forecast_60(
    facility_id: int = Query(..., description="Identifier of the parking facility"),
    db: AsyncSession = Depends(get_db_session),
    service: ForecastingService = Depends(get_forecasting_service),
) -> ForecastSnapshotResponse:
    """
    Generates 60-minute snapshot prediction.
    """
    res = await service.get_forecast_snapshot(db, facility_id, 60)
    return ForecastSnapshotResponse(**res)


@router.post(
    "/custom",
    response_model=CustomForecastResponse,
    status_code=status.HTTP_200_OK,
    summary="Custom interval occupancy prediction",
    description="Generates occupancy forecast for custom interval. Automatically trains model if needed.",
)
async def get_custom_forecast(
    req: CustomForecastRequest,
    export_path: Optional[str] = Query(None, description="Custom dataset export directory path"),
    db: AsyncSession = Depends(get_db_session),
    service: ForecastingService = Depends(get_forecasting_service),
) -> CustomForecastResponse:
    """
    Generates custom horizon prediction.
    """
    res = await service.get_custom_forecast(db, req.facility_id, req.target_minutes, export_path)
    return CustomForecastResponse(**res)
