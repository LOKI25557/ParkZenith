"""
Utilization analytics calculations using Pandas.
"""

from typing import Dict, Any
import pandas as pd
from ai_service.analytics.statistics import safe_mean


def calculate_utilization_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes utilization metrics for facility, zone, slots, and occupancy efficiency.
    """
    if df.empty:
        return {
            "facility_utilization": 0.0,
            "zone_utilization": {},
            "slot_utilization": 0.0,
            "occupancy_efficiency": 0.0,
            "average_available_slots": 0.0,
            "average_occupied_slots": 0.0,
        }

    # Facility utilization: mean of occupancy percentage
    facility_util = safe_mean(df["occupancy_percentage"])

    # Zone utilization: mean of occupancy percentage grouped by zone_id
    zone_util = {}
    if "zone_id" in df.columns:
        zone_groups = df.groupby("zone_id")["occupancy_percentage"].mean().round(2)
        for zone_id, val in zone_groups.items():
            if pd.notna(zone_id):
                zone_util[str(zone_id)] = float(val)

    # Average total, occupied, and available slots
    avg_occupied = safe_mean(df["occupied_slots"])
    avg_available = safe_mean(df["available_slots"])
    avg_total = safe_mean(df["total_slots"])

    # Slot utilization: average occupied / average total (expressed as percentage)
    slot_util = float(round((avg_occupied / avg_total * 100.0), 2)) if avg_total > 0 else 0.0

    # Occupancy efficiency: average occupancy percentage (as a fraction of capacity or percentage)
    # We will represent it as the percentage of slots occupied
    occupancy_eff = facility_util

    return {
        "facility_utilization": facility_util,
        "zone_utilization": zone_util,
        "slot_utilization": slot_util,
        "occupancy_efficiency": occupancy_eff,
        "average_available_slots": avg_available,
        "average_occupied_slots": avg_occupied,
    }
