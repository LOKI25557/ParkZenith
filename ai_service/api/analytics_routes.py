"""
FastAPI router defining Analytics Engine endpoints.
"""

from datetime import datetime, date
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ai_service.api.deps import get_db_session, get_analytics_service
from ai_service.services.analytics_service import AnalyticsService
from ai_service.schemas.analytics import (
    OverviewResponse,
    OccupancyAnalyticsResponse,
    UtilizationAnalyticsResponse,
    ReservationAnalyticsResponse,
    SessionAnalyticsResponse,
    PeakHoursResponse,
    TrendsResponse,
    ReportResponse,
)

router = APIRouter(prefix="/analytics", tags=["Analytics Engine"])


@router.get(
    "/overview",
    response_model=OverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Analytics Overview",
    description="Returns high-level summary metrics (current occupancy, average occupancy, utilization, today's sessions, and reservations) for dashboard.",
)
async def get_overview(
    facility_id: Optional[str] = Query(None, description="Filter by facility ID"),
    start_date: Optional[datetime] = Query(None, description="Start range datetime (UTC)"),
    end_date: Optional[datetime] = Query(None, description="End range datetime (UTC)"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    db: AsyncSession = Depends(get_db_session),
) -> OverviewResponse:
    """Get high-level summary overview."""
    result = await analytics_service.get_overview(
        db=db, facility_id=facility_id, start_date=start_date, end_date=end_date
    )
    return OverviewResponse(**result)


@router.get(
    "/daily",
    response_model=ReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Daily Report",
    description="Compiles structured daily report summarizing occupancy, utilization, reservations, sessions, and peak traffic.",
)
async def get_daily_report(
    facility_id: Optional[str] = Query(None, description="Filter by facility ID"),
    target_date: Optional[date] = Query(None, alias="date", description="Target date for the report (YYYY-MM-DD)"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    db: AsyncSession = Depends(get_db_session),
) -> ReportResponse:
    """Generate daily report."""
    result = await analytics_service.get_daily_report(
        db=db, facility_id=facility_id, target_date=target_date
    )
    # Map report dictionary to Pydantic ReportResponse schema
    return ReportResponse(
        report_type=result["report_type"],
        period=result.get("date"),
        date_range=None,
        occupancy=result["occupancy"],
        utilization=result["utilization"],
        reservations=result["reservations"],
        sessions=result["sessions"],
        traffic=result["traffic"],
    )


@router.get(
    "/weekly",
    response_model=ReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Weekly Report",
    description="Compiles structured weekly report over a date range.",
)
async def get_weekly_report(
    facility_id: Optional[str] = Query(None, description="Filter by facility ID"),
    start_date: Optional[date] = Query(None, description="Start date for the week (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for the week (YYYY-MM-DD)"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    db: AsyncSession = Depends(get_db_session),
) -> ReportResponse:
    """Generate weekly report."""
    result = await analytics_service.get_weekly_report(
        db=db, facility_id=facility_id, start_date=start_date, end_date=end_date
    )
    return ReportResponse(
        report_type=result["report_type"],
        period=None,
        date_range=result["date_range"],
        occupancy=result["occupancy"],
        utilization=result["utilization"],
        reservations=result["reservations"],
        sessions=result["sessions"],
        traffic=result["traffic"],
    )


@router.get(
    "/monthly",
    response_model=ReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Monthly Report",
    description="Compiles structured monthly report.",
)
async def get_monthly_report(
    facility_id: Optional[str] = Query(None, description="Filter by facility ID"),
    year: Optional[int] = Query(None, description="Year of the report (e.g. 2026)"),
    month: Optional[int] = Query(None, description="Month of the report (1-12)"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    db: AsyncSession = Depends(get_db_session),
) -> ReportResponse:
    """Generate monthly report."""
    result = await analytics_service.get_monthly_report(
        db=db, facility_id=facility_id, year=year, month=month
    )
    return ReportResponse(
        report_type=result["report_type"],
        period=result.get("period"),
        date_range=None,
        occupancy=result["occupancy"],
        utilization=result["utilization"],
        reservations=result["reservations"],
        sessions=result["sessions"],
        traffic=result["traffic"],
    )


@router.get(
    "/occupancy",
    response_model=OccupancyAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Detailed Occupancy Analytics",
    description="Computes average, minimum, maximum occupancy metrics, and hourly/daily/weekly/monthly trends.",
)
async def get_occupancy_analytics(
    facility_id: Optional[str] = Query(None, description="Filter by facility ID"),
    start_date: Optional[datetime] = Query(None, description="Start date/time (UTC)"),
    end_date: Optional[datetime] = Query(None, description="End date/time (UTC)"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    db: AsyncSession = Depends(get_db_session),
) -> OccupancyAnalyticsResponse:
    """Get detailed occupancy stats and trends."""
    result = await analytics_service.get_occupancy_analytics(
        db=db, facility_id=facility_id, start_date=start_date, end_date=end_date
    )
    return OccupancyAnalyticsResponse(**result)


@router.get(
    "/utilization",
    response_model=UtilizationAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Utilization Metrics",
    description="Computes space utilization percentage, zone efficiency, and average occupied/available slots.",
)
async def get_utilization_analytics(
    facility_id: Optional[str] = Query(None, description="Filter by facility ID"),
    start_date: Optional[datetime] = Query(None, description="Start date/time (UTC)"),
    end_date: Optional[datetime] = Query(None, description="End date/time (UTC)"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    db: AsyncSession = Depends(get_db_session),
) -> UtilizationAnalyticsResponse:
    """Get utilization analytics."""
    result = await analytics_service.get_utilization_analytics(
        db=db, facility_id=facility_id, start_date=start_date, end_date=end_date
    )
    return UtilizationAnalyticsResponse(**result)


@router.get(
    "/reservations",
    response_model=ReservationAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Reservation Analytics",
    description="Computes reservation success rates, cancellation rates, durations, and booking trends.",
)
async def get_reservation_analytics(
    facility_id: Optional[str] = Query(None, description="Filter by facility ID"),
    start_date: Optional[datetime] = Query(None, description="Start date/time (UTC)"),
    end_date: Optional[datetime] = Query(None, description="End date/time (UTC)"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    db: AsyncSession = Depends(get_db_session),
) -> ReservationAnalyticsResponse:
    """Get reservation analytics."""
    result = await analytics_service.get_reservation_analytics(
        db=db, facility_id=facility_id, start_date=start_date, end_date=end_date
    )
    return ReservationAnalyticsResponse(**result)


@router.get(
    "/sessions",
    response_model=SessionAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Parking Session Analytics",
    description="Computes check-in counts, duration metrics (mean, median, min, max), and duration buckets distribution.",
)
async def get_sessions_analytics(
    facility_id: Optional[str] = Query(None, description="Filter by facility ID"),
    start_date: Optional[datetime] = Query(None, description="Start date/time (UTC)"),
    end_date: Optional[datetime] = Query(None, description="End date/time (UTC)"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    db: AsyncSession = Depends(get_db_session),
) -> SessionAnalyticsResponse:
    """Get parking session analytics."""
    result = await analytics_service.get_session_analytics(
        db=db, facility_id=facility_id, start_date=start_date, end_date=end_date
    )
    return SessionAnalyticsResponse(**result)


@router.get(
    "/peak-hours",
    response_model=PeakHoursResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Peak Hours & Days",
    description="Retrieves busiest and least busy hours/days, as well as occupancy averages hourly.",
)
async def get_peak_hours(
    facility_id: Optional[str] = Query(None, description="Filter by facility ID"),
    start_date: Optional[datetime] = Query(None, description="Start date/time (UTC)"),
    end_date: Optional[datetime] = Query(None, description="End date/time (UTC)"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    db: AsyncSession = Depends(get_db_session),
) -> PeakHoursResponse:
    """Get peak hours and days."""
    result = await analytics_service.get_peak_hours_analytics(
        db=db, facility_id=facility_id, start_date=start_date, end_date=end_date
    )
    return PeakHoursResponse(**result)


@router.get(
    "/trends",
    response_model=TrendsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Historical Trends & Rolling Averages",
    description="Calculates a rolling average of occupancy along with hourly, daily, weekly, and monthly trends.",
)
async def get_trends(
    facility_id: Optional[str] = Query(None, description="Filter by facility ID"),
    start_date: Optional[datetime] = Query(None, description="Start date/time (UTC)"),
    end_date: Optional[datetime] = Query(None, description="End date/time (UTC)"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    db: AsyncSession = Depends(get_db_session),
) -> TrendsResponse:
    """Get rolling averages and trends."""
    result = await analytics_service.get_trends_analytics(
        db=db, facility_id=facility_id, start_date=start_date, end_date=end_date
    )
    return TrendsResponse(**result)
