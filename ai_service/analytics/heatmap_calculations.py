"""
Core mathematical calculations for density, utilization, congestion, and color intensity.
"""

from typing import Union
from ai_service.queue.congestion import classify_congestion


def calculate_occupancy_percentage(occupied_slots: int, total_slots: int) -> float:
    """
    Computes occupancy percentage based on occupied and total slots.
    """
    if total_slots <= 0:
        return 0.0
    return round(min(100.0, max(0.0, (occupied_slots / total_slots) * 100.0)), 2)


def calculate_density_score(occupied_slots: int, total_slots: int) -> float:
    """
    Calculates density score. Under basic conditions, density equals occupancy percentage.
    """
    return calculate_occupancy_percentage(occupied_slots, total_slots)


def calculate_capacity_utilization(occupied_slots: int, total_slots: int) -> float:
    """
    Calculates the capacity utilization percentage.
    """
    return calculate_occupancy_percentage(occupied_slots, total_slots)


def calculate_zone_utilization(occupied_slots: int, total_slots: int) -> float:
    """
    Calculates the zone-specific utilization percentage.
    """
    return calculate_occupancy_percentage(occupied_slots, total_slots)


def calculate_color_intensity(density_score: float) -> float:
    """
    Maps a density score to color intensity score (0–100).
    """
    return round(min(100.0, max(0.0, density_score)), 2)


def calculate_congestion_index(
    occupied_slots: int,
    total_slots: int,
    queue_length: float = 0.0,
    waiting_time_minutes: float = 0.0,
) -> float:
    """
    Computes a numerical congestion index (0 to 100) combining slot occupancy and queue metrics.
    
    Formula:
    congestion_index = occupancy_percentage * 0.8 + min(20.0, queue_length * 2.0 + waiting_time_minutes * 0.5)
    """
    occ_pct = calculate_occupancy_percentage(occupied_slots, total_slots)
    if total_slots <= 0:
        return 0.0
    
    queue_penalty = min(20.0, max(0.0, queue_length * 2.0 + waiting_time_minutes * 0.5))
    congestion_val = occ_pct * 0.8 + queue_penalty
    return round(min(100.0, max(0.0, congestion_val)), 2)


def get_congestion_level(
    occupied_slots: int,
    total_slots: int,
    queue_length: float = 0.0,
    waiting_time_minutes: float = 0.0,
) -> str:
    """
    Retrieves the categorical level (LOW, MODERATE, HIGH, SEVERE) using the existing queue classifier.
    """
    return classify_congestion(
        queue_length=queue_length,
        capacity=total_slots,
        occupied_slots=occupied_slots,
        waiting_time_minutes=waiting_time_minutes,
    )
