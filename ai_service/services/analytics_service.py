"""
AnalyticsService coordinating database repositories and Pandas analytics modules.
"""

import logging
from datetime import datetime, time, timedelta, timezone, date
from typing import Optional, Dict, Any, List
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from ai_service.core.exceptions import (
    EmptyDatasetError,
    MissingFacilityError,
    InvalidDateRangeError,
)
from ai_service.models.occupancy import OccupancyHistory
from ai_service.models.reservation import ReservationHistory
from ai_service.models.session import ParkingSessionHistory
from ai_service.repositories.occupancy_repository import OccupancyRepository
from ai_service.repositories.reservation_repository import ReservationRepository
from ai_service.repositories.session_repository import ParkingSessionRepository

from ai_service.analytics.occupancy import (
    calculate_current_occupancy,
    calculate_occupancy_metrics,
    calculate_hourly_trend,
    calculate_daily_trend,
    calculate_weekly_trend,
    calculate_monthly_trend,
    detect_peak_hours,
)
from ai_service.analytics.utilization import calculate_utilization_metrics
from ai_service.analytics.reservation import calculate_reservation_metrics
from ai_service.analytics.sessions import calculate_session_metrics
from ai_service.analytics.trends import calculate_occupancy_rolling_average
from ai_service.analytics.reports import (
    generate_daily_report,
    generate_weekly_report,
    generate_monthly_report,
    generate_summary_report,
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Service class orchestrating database aggregation and advanced analytics using Pandas.
    """

    def __init__(self) -> None:
        pass

    async def _validate_facility(self, db: AsyncSession, facility_id: Optional[str]) -> None:
        """
        Validates if a facility exists by checking for any historical record.
        Raises MissingFacilityError if facility has no data.
        """
        if not facility_id:
            return

        # Check if facility exists in any of the tables
        occ_stmt = select(func.count()).select_from(OccupancyHistory).where(OccupancyHistory.facility_id == facility_id)
        res_stmt = select(func.count()).select_from(ReservationHistory).where(ReservationHistory.facility_id == facility_id)
        sess_stmt = select(func.count()).select_from(ParkingSessionHistory).where(ParkingSessionHistory.facility_id == facility_id)

        occ_count = (await db.execute(occ_stmt)).scalar() or 0
        res_count = (await db.execute(res_stmt)).scalar() or 0
        sess_count = (await db.execute(sess_stmt)).scalar() or 0

        if occ_count == 0 and res_count == 0 and sess_count == 0:
            raise MissingFacilityError(f"Facility '{facility_id}' has no historical records.")

    def _resolve_dates(
        self, start_date: Optional[datetime], end_date: Optional[datetime]
    ) -> tuple[datetime, datetime]:
        """
        Applies default date range (last 30 days) if not provided, and validates start_date <= end_date.
        """
        if not end_date:
            end_date = datetime.now(timezone.utc)
        if not start_date:
            start_date = end_date - timedelta(days=30)

        if start_date > end_date:
            raise InvalidDateRangeError("Start date cannot be after end date.")

        return start_date, end_date

    async def get_overview(
        self,
        db: AsyncSession,
        facility_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Computes high-level overview metrics for dashboard.
        """
        await self._validate_facility(db, facility_id)
        start, end = self._resolve_dates(start_date, end_date)

        # 1. SQL Aggregate for Average occupied slots & Utilization percentage
        occ_filters = [OccupancyHistory.collected_at >= start, OccupancyHistory.collected_at <= end]
        if facility_id:
            occ_filters.append(OccupancyHistory.facility_id == facility_id)

        avg_occ_stmt = (
            select(
                func.avg(OccupancyHistory.occupied_slots).label("avg_occupied"),
                func.avg(OccupancyHistory.occupancy_percentage).label("avg_percentage"),
            )
            .where(and_(*occ_filters))
        )
        avg_res = (await db.execute(avg_occ_stmt)).first()
        avg_occupied = float(round(avg_res.avg_occupied, 2)) if avg_res and avg_res.avg_occupied is not None else 0.0
        avg_percentage = float(round(avg_res.avg_percentage, 2)) if avg_res and avg_res.avg_percentage is not None else 0.0

        # 2. Get Today's Counts (Midnight to current moment)
        now_utc = datetime.now(timezone.utc)
        today_start = datetime.combine(now_utc.date(), time.min, tzinfo=timezone.utc)
        today_end = datetime.combine(now_utc.date(), time.max, tzinfo=timezone.utc)

        # Today's sessions count
        sess_filters = [
            ParkingSessionHistory.check_in_time >= today_start,
            ParkingSessionHistory.check_in_time <= today_end,
        ]
        if facility_id:
            sess_filters.append(ParkingSessionHistory.facility_id == facility_id)
        sess_today_stmt = select(func.count()).select_from(ParkingSessionHistory).where(and_(*sess_filters))
        today_sessions = (await db.execute(sess_today_stmt)).scalar() or 0

        # Today's reservations count
        res_filters = [
            ReservationHistory.reservation_start >= today_start,
            ReservationHistory.reservation_start <= today_end,
        ]
        if facility_id:
            res_filters.append(ReservationHistory.facility_id == facility_id)
        res_today_stmt = select(func.count()).select_from(ReservationHistory).where(and_(*res_filters))
        today_reservations = (await db.execute(res_today_stmt)).scalar() or 0

        # 3. Reservation count in range
        range_res_filters = [
            ReservationHistory.reservation_start >= start,
            ReservationHistory.reservation_start <= end,
        ]
        if facility_id:
            range_res_filters.append(ReservationHistory.facility_id == facility_id)
        range_res_stmt = select(func.count()).select_from(ReservationHistory).where(and_(*range_res_filters))
        reservation_count = (await db.execute(range_res_stmt)).scalar() or 0

        # 4. Average session duration in range
        range_sess_filters = [
            ParkingSessionHistory.check_in_time >= start,
            ParkingSessionHistory.check_in_time <= end,
        ]
        if facility_id:
            range_sess_filters.append(ParkingSessionHistory.facility_id == facility_id)
        range_sess_stmt = select(func.avg(ParkingSessionHistory.duration_minutes)).where(and_(*range_sess_filters))
        avg_dur = (await db.execute(range_sess_stmt)).scalar()
        avg_session_duration = float(round(avg_dur, 2)) if avg_dur is not None else 0.0

        # 5. Fetch Latest Occupancy
        latest_occ_stmt = select(OccupancyHistory).order_by(OccupancyHistory.collected_at.desc())
        if facility_id:
            latest_occ_stmt = latest_occ_stmt.where(OccupancyHistory.facility_id == facility_id)
        latest_occ_stmt = latest_occ_stmt.limit(1)
        latest_occ_record = (await db.execute(latest_occ_stmt)).scalar_one_or_none()

        current_occupancy = None
        if latest_occ_record:
            current_occupancy = {
                "facility_id": latest_occ_record.facility_id,
                "zone_id": latest_occ_record.zone_id,
                "occupied_slots": latest_occ_record.occupied_slots,
                "available_slots": latest_occ_record.available_slots,
                "total_slots": latest_occ_record.total_slots,
                "occupancy_percentage": float(round(latest_occ_record.occupancy_percentage, 2)),
                "collected_at": latest_occ_record.collected_at.isoformat(),
            }

        # 6. Fetch Occupancy data for peak hour computation using Pandas
        occ_repo = OccupancyRepository(db)
        occ_records = await occ_repo.get_between_dates(start, end, facility_id)
        peak_hour = None
        least_busy_hour = None
        if occ_records:
            occ_df = pd.DataFrame([r.__dict__ for r in occ_records])
            if "_sa_instance_state" in occ_df.columns:
                occ_df.drop(columns=["_sa_instance_state"], inplace=True)
            occ_df["collected_at"] = pd.to_datetime(occ_df["collected_at"])
            peak_data = detect_peak_hours(occ_df)
            if peak_data["peak_hours"]:
                peak_hour = peak_data["peak_hours"][0]
            if peak_data["least_busy_hours"]:
                least_busy_hour = peak_data["least_busy_hours"][0]

        return {
            "facility_id": facility_id,
            "current_occupancy": current_occupancy,
            "average_occupancy": avg_occupied,
            "facility_utilization": avg_percentage,
            "peak_hour": peak_hour,
            "least_busy_hour": least_busy_hour,
            "average_session_duration": avg_session_duration,
            "reservation_count": reservation_count,
            "today_sessions": today_sessions,
            "today_reservations": today_reservations,
        }

    async def get_occupancy_analytics(
        self,
        db: AsyncSession,
        facility_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves historical occupancy and generates trend rollups.
        """
        await self._validate_facility(db, facility_id)
        start, end = self._resolve_dates(start_date, end_date)

        occ_repo = OccupancyRepository(db)
        records = await occ_repo.get_between_dates(start, end, facility_id)
        if not records:
            raise EmptyDatasetError("No occupancy data matches the filters.")

        df = pd.DataFrame([r.__dict__ for r in records])
        if "_sa_instance_state" in df.columns:
            df.drop(columns=["_sa_instance_state"], inplace=True)
        df["collected_at"] = pd.to_datetime(df["collected_at"])

        metrics = calculate_occupancy_metrics(df)
        hourly = calculate_hourly_trend(df)
        daily = calculate_daily_trend(df)
        weekly = calculate_weekly_trend(df)
        monthly = calculate_monthly_trend(df)

        return {
            "average_occupancy": metrics["average_occupancy"],
            "maximum_occupancy": metrics["maximum_occupancy"],
            "minimum_occupancy": metrics["minimum_occupancy"],
            "occupancy_percentage": metrics["occupancy_percentage"],
            "hourly_trend": hourly,
            "daily_trend": daily,
            "weekly_trend": weekly,
            "monthly_trend": monthly,
        }

    async def get_utilization_analytics(
        self,
        db: AsyncSession,
        facility_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Generates utilization analytics including facility, zone, and slot efficiency.
        """
        await self._validate_facility(db, facility_id)
        start, end = self._resolve_dates(start_date, end_date)

        occ_repo = OccupancyRepository(db)
        records = await occ_repo.get_between_dates(start, end, facility_id)
        if not records:
            raise EmptyDatasetError("No occupancy history found for utilization analysis.")

        df = pd.DataFrame([r.__dict__ for r in records])
        if "_sa_instance_state" in df.columns:
            df.drop(columns=["_sa_instance_state"], inplace=True)
        df["collected_at"] = pd.to_datetime(df["collected_at"])

        return calculate_utilization_metrics(df)

    async def get_reservation_analytics(
        self,
        db: AsyncSession,
        facility_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Generates reservation bookings counts, cancellations, success rate, and trends.
        """
        await self._validate_facility(db, facility_id)
        start, end = self._resolve_dates(start_date, end_date)

        res_repo = ReservationRepository(db)
        records = await res_repo.get_between_dates(start, end, facility_id)
        if not records:
            raise EmptyDatasetError("No reservation records found in the specified range.")

        df = pd.DataFrame([r.__dict__ for r in records])
        if "_sa_instance_state" in df.columns:
            df.drop(columns=["_sa_instance_state"], inplace=True)
        df["reservation_start"] = pd.to_datetime(df["reservation_start"])

        return calculate_reservation_metrics(df)

    async def get_session_analytics(
        self,
        db: AsyncSession,
        facility_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Generates parking session duration stats, vehicle type distribution, and distribution buckets.
        """
        await self._validate_facility(db, facility_id)
        start, end = self._resolve_dates(start_date, end_date)

        sess_repo = ParkingSessionRepository(db)
        records = await sess_repo.get_between_dates(start, end, facility_id)
        if not records:
            raise EmptyDatasetError("No parking session records found in the specified range.")

        df = pd.DataFrame([r.__dict__ for r in records])
        if "_sa_instance_state" in df.columns:
            df.drop(columns=["_sa_instance_state"], inplace=True)
        df["check_in_time"] = pd.to_datetime(df["check_in_time"])

        return calculate_session_metrics(df)

    async def get_peak_hours_analytics(
        self,
        db: AsyncSession,
        facility_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Identifies busy/less-busy days and hours of the facility.
        """
        await self._validate_facility(db, facility_id)
        start, end = self._resolve_dates(start_date, end_date)

        occ_repo = OccupancyRepository(db)
        records = await occ_repo.get_between_dates(start, end, facility_id)
        if not records:
            raise EmptyDatasetError("No occupancy records available for peak hour detection.")

        df = pd.DataFrame([r.__dict__ for r in records])
        if "_sa_instance_state" in df.columns:
            df.drop(columns=["_sa_instance_state"], inplace=True)
        df["collected_at"] = pd.to_datetime(df["collected_at"])

        return detect_peak_hours(df)

    async def get_trends_analytics(
        self,
        db: AsyncSession,
        facility_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Calculates hourly, daily, weekly, monthly trends and rolling average.
        """
        await self._validate_facility(db, facility_id)
        start, end = self._resolve_dates(start_date, end_date)

        occ_repo = OccupancyRepository(db)
        records = await occ_repo.get_between_dates(start, end, facility_id)
        if not records:
            raise EmptyDatasetError("No occupancy records available for trend analysis.")

        df = pd.DataFrame([r.__dict__ for r in records])
        if "_sa_instance_state" in df.columns:
            df.drop(columns=["_sa_instance_state"], inplace=True)
        df["collected_at"] = pd.to_datetime(df["collected_at"])

        rolling = calculate_occupancy_rolling_average(df)
        hourly = calculate_hourly_trend(df)
        daily = calculate_daily_trend(df)
        weekly = calculate_weekly_trend(df)
        monthly = calculate_monthly_trend(df)

        return {
            "rolling_average": rolling,
            "hourly_trend": hourly,
            "daily_trend": daily,
            "weekly_trend": weekly,
            "monthly_trend": monthly,
        }

    async def get_daily_report(
        self, db: AsyncSession, facility_id: Optional[str] = None, target_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Compiles structured JSON for daily report on target_date.
        """
        await self._validate_facility(db, facility_id)
        if not target_date:
            target_date = datetime.now(timezone.utc).date()

        day_start = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
        day_end = datetime.combine(target_date, time.max, tzinfo=timezone.utc)

        occ_repo = OccupancyRepository(db)
        res_repo = ReservationRepository(db)
        sess_repo = ParkingSessionRepository(db)

        occ_records = await occ_repo.get_between_dates(day_start, day_end, facility_id)
        res_records = await res_repo.get_between_dates(day_start, day_end, facility_id)
        sess_records = await sess_repo.get_between_dates(day_start, day_end, facility_id)

        if not occ_records and not res_records and not sess_records:
            raise EmptyDatasetError(f"No records found for target date: {target_date}")

        occ_df = pd.DataFrame([r.__dict__ for r in occ_records])
        if not occ_df.empty:
            occ_df.drop(columns=["_sa_instance_state"], errors="ignore", inplace=True)
            occ_df["collected_at"] = pd.to_datetime(occ_df["collected_at"])

        res_df = pd.DataFrame([r.__dict__ for r in res_records])
        if not res_df.empty:
            res_df.drop(columns=["_sa_instance_state"], errors="ignore", inplace=True)
            res_df["reservation_start"] = pd.to_datetime(res_df["reservation_start"])

        sess_df = pd.DataFrame([r.__dict__ for r in sess_records])
        if not sess_df.empty:
            sess_df.drop(columns=["_sa_instance_state"], errors="ignore", inplace=True)
            sess_df["check_in_time"] = pd.to_datetime(sess_df["check_in_time"])

        report = generate_daily_report(occ_df, res_df, sess_df, str(target_date))
        return report

    async def get_weekly_report(
        self, db: AsyncSession, facility_id: Optional[str] = None, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Compiles structured JSON for weekly report.
        """
        await self._validate_facility(db, facility_id)
        if not end_date:
            end_date = datetime.now(timezone.utc).date()
        if not start_date:
            start_date = end_date - timedelta(days=7)

        if start_date > end_date:
            raise InvalidDateRangeError("Start date cannot be after end date.")

        range_start = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
        range_end = datetime.combine(end_date, time.max, tzinfo=timezone.utc)

        occ_repo = OccupancyRepository(db)
        res_repo = ReservationRepository(db)
        sess_repo = ParkingSessionRepository(db)

        occ_records = await occ_repo.get_between_dates(range_start, range_end, facility_id)
        res_records = await res_repo.get_between_dates(range_start, range_end, facility_id)
        sess_records = await sess_repo.get_between_dates(range_start, range_end, facility_id)

        if not occ_records and not res_records and not sess_records:
            raise EmptyDatasetError(f"No records found for week range: {start_date} to {end_date}")

        occ_df = pd.DataFrame([r.__dict__ for r in occ_records])
        if not occ_df.empty:
            occ_df.drop(columns=["_sa_instance_state"], errors="ignore", inplace=True)
            occ_df["collected_at"] = pd.to_datetime(occ_df["collected_at"])

        res_df = pd.DataFrame([r.__dict__ for r in res_records])
        if not res_df.empty:
            res_df.drop(columns=["_sa_instance_state"], errors="ignore", inplace=True)
            res_df["reservation_start"] = pd.to_datetime(res_df["reservation_start"])

        sess_df = pd.DataFrame([r.__dict__ for r in sess_records])
        if not sess_df.empty:
            sess_df.drop(columns=["_sa_instance_state"], errors="ignore", inplace=True)
            sess_df["check_in_time"] = pd.to_datetime(sess_df["check_in_time"])

        report = generate_weekly_report(occ_df, res_df, sess_df, str(start_date), str(end_date))
        return report

    async def get_monthly_report(
        self, db: AsyncSession, facility_id: Optional[str] = None, year: Optional[int] = None, month: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Compiles structured JSON for monthly report.
        """
        await self._validate_facility(db, facility_id)
        now = datetime.now(timezone.utc)
        if not year:
            year = now.year
        if not month:
            month = now.month

        # Calculate start and end of month
        try:
            start_date = date(year, month, 1)
            if month == 12:
                end_date = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(year, month + 1, 1) - timedelta(days=1)
        except ValueError as exc:
            raise InvalidDateRangeError(f"Invalid year/month value: {year}/{month}") from exc

        month_start = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
        month_end = datetime.combine(end_date, time.max, tzinfo=timezone.utc)

        occ_repo = OccupancyRepository(db)
        res_repo = ReservationRepository(db)
        sess_repo = ParkingSessionRepository(db)

        occ_records = await occ_repo.get_between_dates(month_start, month_end, facility_id)
        res_records = await res_repo.get_between_dates(month_start, month_end, facility_id)
        sess_records = await sess_repo.get_between_dates(month_start, month_end, facility_id)

        if not occ_records and not res_records and not sess_records:
            raise EmptyDatasetError(f"No records found for period: {year}-{month:02d}")

        occ_df = pd.DataFrame([r.__dict__ for r in occ_records])
        if not occ_df.empty:
            occ_df.drop(columns=["_sa_instance_state"], errors="ignore", inplace=True)
            occ_df["collected_at"] = pd.to_datetime(occ_df["collected_at"])

        res_df = pd.DataFrame([r.__dict__ for r in res_records])
        if not res_df.empty:
            res_df.drop(columns=["_sa_instance_state"], errors="ignore", inplace=True)
            res_df["reservation_start"] = pd.to_datetime(res_df["reservation_start"])

        sess_df = pd.DataFrame([r.__dict__ for r in sess_records])
        if not sess_df.empty:
            sess_df.drop(columns=["_sa_instance_state"], errors="ignore", inplace=True)
            sess_df["check_in_time"] = pd.to_datetime(sess_df["check_in_time"])

        report = generate_monthly_report(occ_df, res_df, sess_df, year, month)
        return report
