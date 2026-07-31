"""
Geographical distance calculation and candidate filtering stage.
"""

import math
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Configurable road-to-walking multiplier
DEFAULT_WALKING_MULTIPLIER = 1.2


def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes geographical distance in kilometers between two points using the Haversine formula.
    """
    # Earth radius in kilometers
    R = 6371.0

    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(d_lat / 2.0) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def estimate_walking_distance_m(distance_km: float, multiplier: float = DEFAULT_WALKING_MULTIPLIER) -> int:
    """
    Estimates walking distance in meters from road/geographical distance in km.
    Formula: walking_distance_m = distance_km * 1000 * multiplier
    """
    return int(distance_km * 1000.0 * multiplier)


def is_valid_coordinate(lat: Optional[float], lon: Optional[float]) -> bool:
    """
    Checks if latitude is in [-90, 90] and longitude is in [-180, 180].
    """
    if lat is None or lon is None:
        return False
    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0


def filter_candidate_facilities(
    facilities: List[Dict[str, Any]],
    user_latitude: float,
    user_longitude: float,
    max_distance_km: float,
    parking_type: Optional[str] = None,
    accessibility_required: Optional[bool] = False,
    max_parking_fee: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Filters facilities based on radius, active status, valid coordinates, capacity, and user preferences.
    Calculates distance and adds it to the returned dictionary.
    """
    logger.info("Filtering %d candidate facilities. Max radius: %.2f km", len(facilities), max_distance_km)

    if not is_valid_coordinate(user_latitude, user_longitude):
        logger.error("Invalid user coordinates: lat=%s, lon=%s", user_latitude, user_longitude)
        return []

    filtered: List[Dict[str, Any]] = []

    for fac in facilities:
        fac_id = fac.get("facility_id")
        
        # 1. Operational status check
        if not fac.get("is_active", True):
            logger.debug("Facility '%s' filtered out: inactive", fac_id)
            continue

        # 2. Coordinate validity check
        lat = fac.get("latitude")
        lon = fac.get("longitude")
        if not is_valid_coordinate(lat, lon):
            logger.debug("Facility '%s' filtered out: invalid coordinates (lat=%s, lon=%s)", fac_id, lat, lon)
            continue

        # 3. Capacity check
        capacity = fac.get("total_slots", 0)
        if capacity <= 0:
            logger.debug("Facility '%s' filtered out: capacity <= 0", fac_id)
            continue

        # 4. Distance check
        dist = calculate_distance_km(user_latitude, user_longitude, lat, lon)
        if dist > max_distance_km:
            logger.debug("Facility '%s' filtered out: distance %.2f km exceeds max %.2f km", fac_id, dist, max_distance_km)
            continue

        # 5. User preferences: Optional parking type
        if parking_type:
            fac_type = fac.get("parking_type", "")
            if fac_type.lower() != parking_type.lower():
                logger.debug("Facility '%s' filtered out: parking type mismatch (%s != %s)", fac_id, fac_type, parking_type)
                continue

        # 6. User preferences: Accessibility requirements
        if accessibility_required:
            has_acc = fac.get("accessibility", False)
            if not has_acc:
                logger.debug("Facility '%s' filtered out: accessibility required but not supported", fac_id)
                continue

        # 7. User preferences: Maximum parking fee
        if max_parking_fee is not None:
            fee = fac.get("hourly_rate", 0.0)
            if fee > max_parking_fee:
                logger.debug("Facility '%s' filtered out: fee %.2f exceeds max %.2f", fac_id, fee, max_parking_fee)
                continue

        # Store calculated distance in the candidate object
        fac_copy = fac.copy()
        fac_copy["distance_km"] = round(dist, 2)
        fac_copy["walking_distance_m"] = estimate_walking_distance_m(dist)
        filtered.append(fac_copy)

    logger.info("Candidate filtering complete. %d/%d candidates matched filters.", len(filtered), len(facilities))
    return filtered
