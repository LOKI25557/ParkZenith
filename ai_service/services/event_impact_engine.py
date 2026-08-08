"""
Event Impact Engine module.
Calculates distance-decay, temporal weighting, and category-based factors for event impact estimations.
"""

import math
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class EventImpactEngine:
    """
    Algorithmic engine for estimating external event impacts on parking facilities.
    """

    @staticmethod
    def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Haversine formula to compute distance between two coordinates in kilometers.
        """
        # Convert decimal degrees to radians
        d_lat = math.radians(lat2 - lat1)
        d_lon = math.radians(lon2 - lon1)
        r_lat1 = math.radians(lat1)
        r_lat2 = math.radians(lat2)

        # Haversine formula
        a = (math.sin(d_lat / 2) ** 2 +
             math.cos(r_lat1) * math.cos(r_lat2) * math.sin(d_lon / 2) ** 2)
        c = 2 * math.asin(math.sqrt(a))
        r = 6371.0  # Radius of Earth in kilometers
        return round(c * r, 2)

    @staticmethod
    def get_time_weight(start_time: datetime, end_time: datetime, target_time: datetime) -> float:
        """
        Computes temporal weighting factor (0.0 to 1.0) based on prediction target time.
        Ramps up 2 hours before the event starts, stays at 1.0 during the event, and ramps down 2 hours after it ends.
        """
        # Ensure timezone comparison compatibility
        if target_time.tzinfo is None:
            target_time = target_time.replace(tzinfo=timezone.utc)
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)

        window_start = start_time - timedelta(hours=2)
        window_end = end_time + timedelta(hours=2)

        if target_time < window_start or target_time > window_end:
            return 0.0

        if target_time <= start_time:
            # Linear ramp-up from 0.0 to 1.0 in the 2 hours before event start
            total_sec = (start_time - window_start).total_seconds()
            elapsed_sec = (target_time - window_start).total_seconds()
            return elapsed_sec / total_sec if total_sec > 0 else 1.0

        if target_time <= end_time:
            # Maximum impact during the event
            return 1.0

        # Linear ramp-down from 1.0 to 0.0 in the 2 hours after event end
        total_sec = (window_end - end_time).total_seconds()
        remaining_sec = (window_end - target_time).total_seconds()
        return remaining_sec / total_sec if total_sec > 0 else 0.0

    @classmethod
    def calculate_impact(
        cls,
        event_type: str,
        expected_attendance: int,
        start_time: datetime,
        end_time: datetime,
        confidence_score: float,
        event_lat: float,
        event_lon: float,
        radius_of_influence: float,
        facility_id: str,
        facility_lat: float,
        facility_lon: float,
        facility_capacity: int,
        target_time: datetime,
        predicted_extra_demand_override: Optional[float] = None,
        congestion_multiplier_override: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Calculates detailed impact metrics of a single event on a facility.
        """
        # 1. Compute distance and decay factor
        distance = cls.calculate_distance_km(event_lat, event_lon, facility_lat, facility_lon)
        if distance > radius_of_influence or radius_of_influence <= 0:
            return {
                "distance_km": distance,
                "attendance_impact": 0.0,
                "extra_occupancy_percentage": 0.0,
                "expected_congestion_level": "LOW",
                "queue_wait_increase_minutes": 0.0,
                "facility_utilization_increase_percentage": 0.0,
                "parking_demand_surge_multiplier": 1.0,
                "travel_delay_minutes": 0.0,
            }

        distance_decay = (radius_of_influence - distance) / radius_of_influence

        # 2. Compute time weight
        time_weight = cls.get_time_weight(start_time, end_time, target_time)
        if time_weight <= 0.0:
            return {
                "distance_km": distance,
                "attendance_impact": 0.0,
                "extra_occupancy_percentage": 0.0,
                "expected_congestion_level": "LOW",
                "queue_wait_increase_minutes": 0.0,
                "facility_utilization_increase_percentage": 0.0,
                "parking_demand_surge_multiplier": 1.0,
                "travel_delay_minutes": 0.0,
            }

        # 3. Categorical default factors
        # Baseline extra occupancy, congestion multiplier, travel delays
        category = event_type.lower()
        if "concert" in category:
            base_occ = 25.0
            base_cong = 1.8
            base_delay = 10.0
        elif "sport" in category or "match" in category or "football" in category:
            base_occ = 35.0
            base_cong = 2.0
            base_delay = 15.0
        elif "festival" in category:
            base_occ = 20.0
            base_cong = 1.4
            base_delay = 8.0
        elif "conference" in category:
            base_occ = 10.0
            base_cong = 1.2
            base_delay = 3.0
        elif "exhibition" in category:
            base_occ = 15.0
            base_cong = 1.3
            base_delay = 5.0
        elif "gathering" in category:
            base_occ = 15.0
            base_cong = 1.4
            base_delay = 6.0
        elif "religious" in category:
            base_occ = 12.0
            base_cong = 1.3
            base_delay = 4.0
        elif "shopping" in category or "sale" in category:
            base_occ = 20.0
            base_cong = 1.5
            base_delay = 6.0
        elif "emergency" in category or "incident" in category:
            base_occ = 30.0
            base_cong = 2.5
            base_delay = 20.0
        elif "road" in category or "closure" in category:
            base_occ = 15.0
            base_cong = 2.5
            base_delay = 20.0
        else:
            base_occ = 15.0
            base_cong = 1.3
            base_delay = 5.0

        # Overrides
        if predicted_extra_demand_override is not None:
            base_occ = predicted_extra_demand_override
        if congestion_multiplier_override is not None:
            base_cong = congestion_multiplier_override

        # 4. Attendance scaling (base values scale up or down relative to a 10,000 attendance event)
        attendance_scale = expected_attendance / 10000.0 if expected_attendance > 0 else 1.0
        attendance_scale = min(3.0, max(0.5, attendance_scale))  # limit scale range

        # 5. Background temporal scale (weekday commute hours boost traffic impact)
        time_scale = 1.0
        if 0 <= target_time.weekday() <= 4:  # Monday to Friday
            if 8 <= target_time.hour <= 10 or 17 <= target_time.hour <= 19:
                time_scale = 1.25

        # 6. Final computations
        factor = distance_decay * time_weight * attendance_scale * confidence_score * time_scale

        extra_occ = base_occ * factor
        # Ensure it doesn't overflow completely
        extra_occ = min(90.0, max(0.0, extra_occ))

        cong_mult = 1.0 + (base_cong - 1.0) * factor
        cong_mult = min(5.0, max(1.0, cong_mult))

        queue_wait = base_delay * factor
        travel_delay = base_delay * factor

        # Categorize congestion level
        if cong_mult >= 2.0:
            cong_lvl = "SEVERE"
        elif cong_mult >= 1.5:
            cong_lvl = "HIGH"
        elif cong_mult >= 1.2:
            cong_lvl = "MEDIUM"
        else:
            cong_lvl = "LOW"

        # Surge multiplier
        surge = 1.0 + 0.5 * factor

        return {
            "distance_km": round(distance, 2),
            "attendance_impact": round(expected_attendance * distance_decay, 2),
            "extra_occupancy_percentage": round(extra_occ, 2),
            "congestion_multiplier": round(cong_mult, 2),
            "expected_congestion_level": cong_lvl,
            "queue_wait_increase_minutes": round(queue_wait, 2),
            "facility_utilization_increase_percentage": round(extra_occ, 2),
            "parking_demand_surge_multiplier": round(surge, 2),
            "travel_delay_minutes": round(travel_delay, 2),
        }
