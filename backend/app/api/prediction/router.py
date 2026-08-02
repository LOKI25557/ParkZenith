from typing import Optional
from fastapi import APIRouter, Query, HTTPException, status

from backend.app.services.ai_service_client import ai_service_client
from backend.app.schemas.prediction import RecommendationRequestSchema

router = APIRouter(prefix="/prediction", tags=["prediction"])


def handle_client_response(res: dict):
    """
    Helper to extract data or raise appropriate HTTP exceptions based on client error codes.
    """
    if not res.get("success", False):
        err = res.get("error", {})
        code = err.get("code")
        message = err.get("message", "AI Service encountered an error.")
        status_code = err.get("status_code", 500)

        if code in ("AI_SERVICE_UNAVAILABLE", "AI_SERVICE_TIMEOUT", "MODEL_UNAVAILABLE"):
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=message)
        elif code in ("MISSING_FACILITY", "EMPTY_DATASET"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        elif code in ("INVALID_DATE_RANGE", "INSUFFICIENT_DATA", "DUPLICATE_DATA"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
        else:
            raise HTTPException(status_code=status_code, detail=message)
    return res.get("data")


@router.get("/ping")
async def ping_prediction():
    return {"message": "prediction service connected"}


@router.get("/occupancy/{facility_id}")
async def get_occupancy_forecast(
    facility_id: int,
    horizon_minutes: int = Query(15, ge=1, description="Horizon in minutes (15, 30, 60 or custom)"),
):
    """
    Retrieves occupancy prediction forecasts for a parking facility.
    """
    res = await ai_service_client.get_occupancy_prediction(facility_id, horizon_minutes)
    return handle_client_response(res)


@router.get("/availability/{facility_id}")
async def get_availability_forecast(
    facility_id: str,
    eta_minutes: int = Query(20, ge=0, description="Estimated arrival time in minutes"),
):
    """
    Retrieves arrival availability probability for a facility.
    """
    res = await ai_service_client.get_availability_prediction(facility_id, eta_minutes)
    return handle_client_response(res)


@router.post("/recommendations")
async def get_recommendations(req: RecommendationRequestSchema):
    """
    Query the Smart Recommendation Engine to find and rank parking spaces.
    """
    res = await ai_service_client.get_recommendations(
        latitude=req.latitude,
        longitude=req.longitude,
        eta_minutes=req.eta_minutes,
        destination_latitude=req.destination_latitude,
        destination_longitude=req.destination_longitude,
        max_distance_km=req.max_distance_km,
        max_results=req.max_results,
        max_parking_fee=req.max_parking_fee,
        parking_type=req.parking_type,
        preferred_facility=req.preferred_facility,
        accessibility_required=req.accessibility_required,
        weights=req.weights,
    )
    return handle_client_response(res)


@router.get("/queue/{facility_id}")
async def get_queue_metrics(
    facility_id: str,
    eta_minutes: Optional[int] = Query(None, ge=0, description="Prediction horizon in minutes"),
):
    """
    Retrieves current queue estimation or future queue prediction at ETA.
    """
    if eta_minutes is not None:
        res = await ai_service_client.get_queue_prediction(facility_id, eta_minutes)
    else:
        res = await ai_service_client.get_queue_status(facility_id)
    return handle_client_response(res)

