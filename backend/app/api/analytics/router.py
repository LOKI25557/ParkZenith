from typing import Optional
from datetime import date
from fastapi import APIRouter, Query, HTTPException, status

from backend.app.services.ai_service_client import ai_service_client

router = APIRouter(prefix="/analytics", tags=["analytics"])


def handle_client_response(res: dict):
    """
    Helper to extract data or raise appropriate HTTP exceptions.
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
async def ping_analytics():
    return {"message": "analytics service connected"}


@router.get("/overview")
async def get_analytics_overview(
    facility_id: Optional[str] = Query(None, description="Filter by facility ID"),
    start_date: Optional[str] = Query(None, description="Start date range in ISO-8601 (UTC)"),
    end_date: Optional[str] = Query(None, description="End date range in ISO-8601 (UTC)"),
):
    """
    Retrieves high-level summary overview of analytics metrics.
    """
    res = await ai_service_client.get_analytics_overview(facility_id, start_date, end_date)
    return handle_client_response(res)


@router.get("/reports/daily")
async def get_daily_report(
    facility_id: Optional[str] = Query(None, description="Filter by facility ID"),
    target_date: Optional[date] = Query(None, description="Target date for the report (YYYY-MM-DD)"),
):
    """
    Retrieves compiled daily report statistics.
    """
    date_str = target_date.strftime("%Y-%m-%d") if target_date else None
    res = await ai_service_client.get_daily_report(facility_id, date_str)
    return handle_client_response(res)


@router.get("/reports/weekly")
async def get_weekly_report(
    facility_id: Optional[str] = Query(None, description="Filter by facility ID"),
    start_date: Optional[date] = Query(None, description="Start date of weekly range (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date of weekly range (YYYY-MM-DD)"),
):
    """
    Retrieves compiled weekly report statistics.
    """
    start_str = start_date.strftime("%Y-%m-%d") if start_date else None
    end_str = end_date.strftime("%Y-%m-%d") if end_date else None
    res = await ai_service_client.get_weekly_report(facility_id, start_str, end_str)
    return handle_client_response(res)

