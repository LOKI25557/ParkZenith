"""
Heatmap Intelligence Service.
Coordinates database access, density/congestion calculations, historical pandas resampling, and zone analytics.
"""

import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ai_service.core.exceptions import MissingFacilityError, EmptyDatasetError
from ai_service.models.occupancy import OccupancyHistory
from ai_service.repositories.occupancy_repository import OccupancyRepository
from ai_service.recommendation.weights import get_facility_metadata, DEFAULT_FACILITY_REGISTRY
from ai_service.analytics.heatmap_calculations import (
    calculate_density_score,
    calculate_occupancy_percentage,
    calculate_congestion_index,
    calculate_capacity_utilization,
    calculate_zone_utilization,
    calculate_color_intensity,
    get_congestion_level,
)
from ai_service.schemas.heatmap import (
    HeatmapPoint,
    ZoneDensity,
    CongestionScore,
    FacilityHeatmap,
    LiveHeatmap,
    HistoricalHeatmap,
    ZoneAnalyticsResponse,
    PeakCongestionPeriod,
)

logger = logging.getLogger(__name__)


class HeatmapService:
    """
    Heatmap Intelligence Service managing spatial-temporal density mapping and congestion metrics.
    """

    def _generate_zone_coordinates(self, fac_lat: float, fac_lon: float, index: int) -> tuple[float, float]:
        """
        Generates deterministic spatial offsets for parking zones surrounding a facility center.
        """
        # Spreads zones out in a circle of approx ~50 meters radius (approx 0.00045 degrees)
        angle = (index * math.pi) / 4.0
        offset_lat = 0.00045 * math.sin(angle)
        offset_lon = 0.00045 * math.cos(angle)
        return round(fac_lat + offset_lat, 6), round(fac_lon + offset_lon, 6)

    async def get_live_heatmap(self, db: AsyncSession) -> LiveHeatmap:
        """
        Computes live heatmap density and congestion scores across all active facilities.
        """
        # 1. Resolve active facility IDs
        stmt = select(OccupancyHistory.facility_id).distinct()
        db_fac_ids = (await db.execute(stmt)).scalars().all()
        
        all_fac_ids = list(set(list(DEFAULT_FACILITY_REGISTRY.keys()) + [str(fid) for fid in db_fac_ids]))
        
        facilities_heatmap: List[FacilityHeatmap] = []
        
        for fid in all_fac_ids:
            try:
                fac_meta = get_facility_metadata(fid)
                fac_lat = fac_meta.get("latitude", 12.9716)
                fac_lon = fac_meta.get("longitude", 77.5946)
                fac_name = fac_meta.get("name", f"Facility {fid}")
                fac_capacity = fac_meta.get("total_slots", 100)

                # Fetch latest facility-level occupancy (zone_id IS NULL or zone_id = '')
                stmt_occ = (
                    select(OccupancyHistory)
                    .where(
                        and_(
                            OccupancyHistory.facility_id == fid,
                            OccupancyHistory.zone_id.is_(None)
                        )
                    )
                    .order_by(OccupancyHistory.collected_at.desc())
                    .limit(1)
                )
                latest_fac_occ = (await db.execute(stmt_occ)).scalar_one_or_none()

                # Fetch all distinct zone ids recorded for this facility
                stmt_zones = (
                    select(OccupancyHistory.zone_id)
                    .distinct()
                    .where(
                        and_(
                            OccupancyHistory.facility_id == fid,
                            OccupancyHistory.zone_id.isnot(None),
                            OccupancyHistory.zone_id != ""
                        )
                    )
                )
                active_zones = (await db.execute(stmt_zones)).scalars().all()

                zone_densities: List[ZoneDensity] = []
                points: List[HeatmapPoint] = []
                
                occupied_sum = 0
                total_slots_sum = 0
                
                # Fetch latest record for each active zone
                for idx, zid in enumerate(active_zones):
                    stmt_zone_occ = (
                        select(OccupancyHistory)
                        .where(
                            and_(
                                OccupancyHistory.facility_id == fid,
                                OccupancyHistory.zone_id == zid
                            )
                        )
                        .order_by(OccupancyHistory.collected_at.desc())
                        .limit(1)
                    )
                    latest_zone_occ = (await db.execute(stmt_zone_occ)).scalar_one_or_none()
                    
                    if latest_zone_occ:
                        z_occupied = latest_zone_occ.occupied_slots
                        z_total = latest_zone_occ.total_slots
                    else:
                        z_occupied = 0
                        z_total = int(fac_capacity / max(1, len(active_zones)))

                    occupied_sum += z_occupied
                    total_slots_sum += z_total
                    
                    z_density = calculate_density_score(z_occupied, z_total)
                    z_occ_pct = calculate_occupancy_percentage(z_occupied, z_total)
                    z_intensity = calculate_color_intensity(z_density)
                    z_lat, z_lon = self._generate_zone_coordinates(fac_lat, fac_lon, idx)
                    
                    zone_densities.append(
                        ZoneDensity(
                            zone_id=zid,
                            density_score=z_density,
                            occupancy_percentage=z_occ_pct,
                            occupied_slots=z_occupied,
                            total_slots=z_total,
                            intensity=z_intensity,
                        )
                    )
                    
                    points.append(
                        HeatmapPoint(
                            latitude=z_lat,
                            longitude=z_lon,
                            intensity=z_intensity,
                            zone_id=zid,
                            facility_id=fid,
                        )
                    )

                # Fallback to hypothetical zones if database contains no zone-specific history
                if not zone_densities:
                    mock_zones = ["ZONE-A", "ZONE-B"]
                    fac_occupied = latest_fac_occ.occupied_slots if latest_fac_occ else 0
                    
                    for idx, zid in enumerate(mock_zones):
                        # Split total capacity and occupancy
                        z_total = int(fac_capacity / 2)
                        z_occupied = int(fac_occupied / 2) if idx == 0 else (fac_occupied - int(fac_occupied / 2))
                        
                        z_density = calculate_density_score(z_occupied, z_total)
                        z_occ_pct = calculate_occupancy_percentage(z_occupied, z_total)
                        z_intensity = calculate_color_intensity(z_density)
                        z_lat, z_lon = self._generate_zone_coordinates(fac_lat, fac_lon, idx)
                        
                        zone_densities.append(
                            ZoneDensity(
                                zone_id=zid,
                                density_score=z_density,
                                occupancy_percentage=z_occ_pct,
                                occupied_slots=z_occupied,
                                total_slots=z_total,
                                intensity=z_intensity,
                            )
                        )
                        
                        points.append(
                            HeatmapPoint(
                                latitude=z_lat,
                                longitude=z_lon,
                                intensity=z_intensity,
                                zone_id=zid,
                                facility_id=fid,
                            )
                        )
                        
                        occupied_sum += z_occupied
                        total_slots_sum += z_total

                # Calculate overall facility metrics
                final_occupied = latest_fac_occ.occupied_slots if latest_fac_occ else occupied_sum
                final_total = latest_fac_occ.total_slots if latest_fac_occ else total_slots_sum
                if final_total <= 0:
                    final_total = fac_capacity
                
                overall_density = calculate_density_score(final_occupied, final_total)
                congestion_idx = calculate_congestion_index(
                    final_occupied, final_total, queue_length=0.0, waiting_time_minutes=0.0
                )
                congestion_lvl = get_congestion_level(final_occupied, final_total)
                cap_util = calculate_capacity_utilization(final_occupied, final_total)
                
                avg_zone_util = sum(z.occupancy_percentage for z in zone_densities) / len(zone_densities) if zone_densities else cap_util

                # Add overall facility center heatmap point
                points.append(
                    HeatmapPoint(
                        latitude=fac_lat,
                        longitude=fac_lon,
                        intensity=calculate_color_intensity(overall_density),
                        zone_id=None,
                        facility_id=fid,
                    )
                )

                facilities_heatmap.append(
                    FacilityHeatmap(
                        facility_id=fid,
                        facility_name=fac_name,
                        latitude=fac_lat,
                        longitude=fac_lon,
                        overall_density=overall_density,
                        overall_congestion_score=CongestionScore(
                            congestion_index=congestion_idx,
                            congestion_level=congestion_lvl,
                            capacity_utilization=cap_util,
                            zone_utilization=avg_zone_util,
                        ),
                        points=points,
                        zones=zone_densities,
                    )
                )
            except Exception as exc:
                logger.error("Failed to generate live heatmap for facility %s: %s", fid, str(exc))

        return LiveHeatmap(
            timestamp=datetime.now(timezone.utc),
            facilities=facilities_heatmap,
        )

    async def get_historical_heatmap(
        self,
        db: AsyncSession,
        start_time: datetime,
        end_time: datetime,
        interval: str,
        facility_id: Optional[str] = None,
    ) -> HistoricalHeatmap:
        """
        Generates resampled historical heatmap trend data using Pandas.
        """
        if start_time > end_time:
            raise ValueError("Start time cannot be after end time.")

        # Fetch records
        repo = OccupancyRepository(db)
        records = await repo.get_between_dates(start_time, end_time, facility_id)

        if not records:
            raise EmptyDatasetError("No historical occupancy data found in the requested range.")

        # Load into DataFrame
        df = pd.DataFrame([r.__dict__ for r in records])
        if "_sa_instance_state" in df.columns:
            df.drop(columns=["_sa_instance_state"], inplace=True)
            
        df["collected_at"] = pd.to_datetime(df["collected_at"]).dt.tz_localize(None)
        
        # Floor timestamps based on interval
        interval = interval.lower()
        if interval == "hourly":
            df["time_key"] = df["collected_at"].dt.floor("h")
        elif interval == "daily":
            df["time_key"] = df["collected_at"].dt.floor("D")
        elif interval == "weekly":
            df["time_key"] = df["collected_at"].dt.to_period("W").dt.to_timestamp()
        elif interval == "monthly":
            df["time_key"] = df["collected_at"].dt.to_period("M").dt.to_timestamp()
        else:
            df["time_key"] = df["collected_at"].dt.floor("h")

        # Group by time_key and facility_id
        grouped = df.groupby(["time_key", "facility_id"])
        
        facilities_heatmap: List[FacilityHeatmap] = []
        
        # We construct facility heatmaps for the overall averages or grouped timestamps
        # To align with the schema, we return the aggregated state per facility in this range.
        # Alternatively, we could group by time_key and return a list of FacilityHeatmaps.
        # Since HistoricalHeatmap takes `facilities: List[FacilityHeatmap]`, we will compute
        # the overall average state per facility during the range resampled, OR we can generate
        # list of facility heatmaps representing the averages across the intervals.
        # Let's generate a merged list of facilities representing the historical resampled status.
        
        unique_facilities = df["facility_id"].unique()
        for fid in unique_facilities:
            fac_df = df[df["facility_id"] == fid]
            fac_meta = get_facility_metadata(str(fid))
            fac_lat = fac_meta.get("latitude", 12.9716)
            fac_lon = fac_meta.get("longitude", 77.5946)
            fac_name = fac_meta.get("name", f"Facility {fid}")
            fac_capacity = fac_meta.get("total_slots", 100)

            # Average occupancy
            fac_overall_df = fac_df[fac_df["zone_id"].isna() | (fac_df["zone_id"] == "")]
            if fac_overall_df.empty:
                fac_overall_df = fac_df

            avg_occupied = float(fac_overall_df["occupied_slots"].mean())
            avg_total = float(fac_overall_df["total_slots"].mean())

            if pd.isna(avg_total) or avg_total <= 0:
                avg_total = fac_capacity
            if pd.isna(avg_occupied):
                avg_occupied = 0.0

            overall_density = calculate_density_score(int(avg_occupied), int(avg_total))
            congestion_idx = calculate_congestion_index(
                int(avg_occupied), int(avg_total), queue_length=0.0, waiting_time_minutes=0.0
            )
            congestion_lvl = get_congestion_level(int(avg_occupied), int(avg_total))
            cap_util = calculate_capacity_utilization(int(avg_occupied), int(avg_total))

            # Group zones
            zone_densities: List[ZoneDensity] = []
            points: List[HeatmapPoint] = []
            
            zone_groups = fac_df.groupby("zone_id")
            idx = 0
            for zid, z_df in zone_groups:
                if pd.isna(zid) or zid == "":
                    continue
                z_avg_occ = float(z_df["occupied_slots"].mean())
                z_avg_tot = float(z_df["total_slots"].mean())
                if pd.isna(z_avg_tot) or z_avg_tot <= 0:
                    z_avg_tot = fac_capacity / 2
                if pd.isna(z_avg_occ):
                    z_avg_occ = 0.0
                
                z_density = calculate_density_score(int(z_avg_occ), int(z_avg_tot))
                z_occ_pct = calculate_occupancy_percentage(int(z_avg_occ), int(z_avg_tot))
                z_intensity = calculate_color_intensity(z_density)
                z_lat, z_lon = self._generate_zone_coordinates(fac_lat, fac_lon, idx)
                
                zone_densities.append(
                    ZoneDensity(
                        zone_id=str(zid),
                        density_score=z_density,
                        occupancy_percentage=z_occ_pct,
                        occupied_slots=int(z_avg_occ),
                        total_slots=int(z_avg_tot),
                        intensity=z_intensity,
                    )
                )
                points.append(
                    HeatmapPoint(
                        latitude=z_lat,
                        longitude=z_lon,
                        intensity=z_intensity,
                        zone_id=str(zid),
                        facility_id=str(fid),
                    )
                )
                idx += 1

            if not zone_densities:
                # Mock zones
                mock_zones = ["ZONE-A", "ZONE-B"]
                for i, zid in enumerate(mock_zones):
                    z_avg_tot = int(avg_total / 2)
                    z_avg_occ = int(avg_occupied / 2) if i == 0 else (int(avg_occupied) - int(avg_occupied / 2))
                    
                    z_density = calculate_density_score(z_avg_occ, z_avg_tot)
                    z_occ_pct = calculate_occupancy_percentage(z_avg_occ, z_avg_tot)
                    z_intensity = calculate_color_intensity(z_density)
                    z_lat, z_lon = self._generate_zone_coordinates(fac_lat, fac_lon, i)
                    
                    zone_densities.append(
                        ZoneDensity(
                            zone_id=zid,
                            density_score=z_density,
                            occupancy_percentage=z_occ_pct,
                            occupied_slots=z_avg_occ,
                            total_slots=z_avg_tot,
                            intensity=z_intensity,
                        )
                    )
                    points.append(
                        HeatmapPoint(
                            latitude=z_lat,
                            longitude=z_lon,
                            intensity=z_intensity,
                            zone_id=zid,
                            facility_id=str(fid),
                        )
                    )

            # Add main facility center point
            points.append(
                HeatmapPoint(
                    latitude=fac_lat,
                    longitude=fac_lon,
                    intensity=calculate_color_intensity(overall_density),
                    zone_id=None,
                    facility_id=str(fid),
                )
            )

            avg_zone_util = sum(z.occupancy_percentage for z in zone_densities) / len(zone_densities) if zone_densities else cap_util

            facilities_heatmap.append(
                FacilityHeatmap(
                    facility_id=str(fid),
                    facility_name=fac_name,
                    latitude=fac_lat,
                    longitude=fac_lon,
                    overall_density=overall_density,
                    overall_congestion_score=CongestionScore(
                        congestion_index=congestion_idx,
                        congestion_level=congestion_lvl,
                        capacity_utilization=cap_util,
                        zone_utilization=avg_zone_util,
                    ),
                    points=points,
                    zones=zone_densities,
                )
            )

        return HistoricalHeatmap(
            start_time=start_time,
            end_time=end_time,
            interval=interval,
            facilities=facilities_heatmap,
        )

    async def get_zone_analytics(
        self,
        db: AsyncSession,
        facility_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> ZoneAnalyticsResponse:
        """
        Performs AI spatial-temporal congestion analysis across parking zones.
        """
        # Resolve start/end dates (default last 30 days)
        if not end_date:
            end_date = datetime.now(timezone.utc)
        if not start_date:
            start_date = end_date - timedelta(days=30)

        repo = OccupancyRepository(db)
        records = await repo.get_between_dates(start_date, end_date, facility_id)

        if not records:
            # Fallback to live snapshot if no historical data exists
            live_snap = await self.get_live_heatmap(db)
            zones_list: List[ZoneDensity] = []
            for f in live_snap.facilities:
                if not facility_id or f.facility_id == facility_id:
                    zones_list.extend(f.zones)

            if not zones_list:
                return ZoneAnalyticsResponse(
                    most_congested_zones=[],
                    least_occupied_zones=[],
                    average_density=0.0,
                    peak_congestion_periods=[],
                    heatmap_summaries={"general": "No zone data available to compile analytics."},
                    zones=[],
                )
            
            # Sort zones
            sorted_zones = sorted(zones_list, key=lambda z: z.density_score, reverse=True)
            most_congested = [z.zone_id for z in sorted_zones[:2]]
            least_occupied = [z.zone_id for z in reversed(sorted_zones)][:2]
            avg_density = sum(z.density_score for z in zones_list) / len(zones_list)

            return ZoneAnalyticsResponse(
                most_congested_zones=most_congested,
                least_occupied_zones=least_occupied,
                average_density=round(avg_density, 2),
                peak_congestion_periods=[PeakCongestionPeriod(period="Live Snapshot", density=round(avg_density, 2))],
                heatmap_summaries={
                    "general": f"Analysis compiled from live snapshot. Most congested zone is '{most_congested[0] if most_congested else 'None'}'."
                },
                zones=zones_list,
            )

        df = pd.DataFrame([r.__dict__ for r in records])
        if "_sa_instance_state" in df.columns:
            df.drop(columns=["_sa_instance_state"], inplace=True)
            
        df["collected_at"] = pd.to_datetime(df["collected_at"]).dt.tz_localize(None)

        # Separate zone data
        zone_df = df[df["zone_id"].notna() & (df["zone_id"] != "")].copy()

        
        # If database only contains facility records, use hypothetical split
        if zone_df.empty:
            # Recreate zone entries dynamically from facility data
            mock_records = []
            for _, row in df.iterrows():
                fac_cap = row["total_slots"]
                fac_occ = row["occupied_slots"]
                
                # Split A
                z_tot_a = int(fac_cap / 2)
                z_occ_a = int(fac_occ / 2)
                # Split B
                z_tot_b = fac_cap - z_tot_a
                z_occ_b = fac_occ - z_occ_a
                
                mock_records.append({
                    "facility_id": row["facility_id"],
                    "zone_id": "ZONE-A",
                    "total_slots": z_tot_a,
                    "occupied_slots": z_occ_a,
                    "collected_at": row["collected_at"]
                })
                mock_records.append({
                    "facility_id": row["facility_id"],
                    "zone_id": "ZONE-B",
                    "total_slots": z_tot_b,
                    "occupied_slots": z_occ_b,
                    "collected_at": row["collected_at"]
                })
            zone_df = pd.DataFrame(mock_records)

        # Calculate density and occupancy averages per zone
        zone_df["density"] = (zone_df["occupied_slots"] / zone_df["total_slots"] * 100.0).fillna(0.0)
        zone_summary = zone_df.groupby("zone_id").agg({
            "density": "mean",
            "occupied_slots": "mean",
            "total_slots": "mean"
        })

        zones_list = []
        for zid, row in zone_summary.iterrows():
            density = round(float(row["density"]), 2)
            zones_list.append(
                ZoneDensity(
                    zone_id=str(zid),
                    density_score=density,
                    occupancy_percentage=density,
                    occupied_slots=int(row["occupied_slots"]),
                    total_slots=int(row["total_slots"]),
                    intensity=calculate_color_intensity(density),
                )
            )

        # Rank zones
        sorted_summary = zone_summary.sort_values(by="density", ascending=False)
        most_congested = [str(z) for z in sorted_summary.index[:2].tolist()]
        least_occupied = [str(z) for z in sorted_summary.index[::-1][:2].tolist()]
        avg_density = round(float(zone_df["density"].mean()), 2)

        # Peak hours analysis
        zone_df["hour"] = zone_df["collected_at"].dt.hour
        hourly_density = zone_df.groupby("hour")["density"].mean()
        peak_hours = hourly_density.sort_values(ascending=False).head(3)
        
        peak_periods = []
        for h, dens in peak_hours.items():
            start_h = f"{h:02d}:00"
            end_h = f"{(h+1)%24:02d}:00"
            peak_periods.append(
                PeakCongestionPeriod(
                    period=f"{start_h} - {end_h}",
                    density=round(float(dens), 2)
                )
            )

        # Generate summary messages
        summaries = {
            "most_congested": f"Zone '{most_congested[0]}' exhibits peak occupancy density, averaging {zone_summary.loc[most_congested[0], 'density']:.1f}% utilization." if most_congested else "No congestion detected.",
            "least_occupied": f"Zone '{least_occupied[0]}' has the highest vacancy availability, averaging {100.0 - zone_summary.loc[least_occupied[0], 'density']:.1f}% free slots." if least_occupied else "No free slots detected.",
            "general_status": f"The average spatial density across parking zones is {avg_density:.1f}% with peak traffic congestion occurring around {peak_periods[0].period if peak_periods else 'unknown'}."
        }

        return ZoneAnalyticsResponse(
            most_congested_zones=most_congested,
            least_occupied_zones=least_occupied,
            average_density=avg_density,
            peak_congestion_periods=peak_periods,
            heatmap_summaries=summaries,
            zones=zones_list,
        )
