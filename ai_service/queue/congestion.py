"""
Queue Congestion Classifier.
Classifies the level of congestion (LOW, MODERATE, HIGH, SEVERE) based on queue and occupancy metrics.
"""

import logging

logger = logging.getLogger(__name__)

def classify_congestion(
    queue_length: float,
    capacity: int,
    occupied_slots: int,
    waiting_time_minutes: float,
) -> str:
    """
    Classifies the congestion level.
    
    Thresholds:
    - LOW: waiting_time_minutes < 2.0 AND occupancy < 70% AND queue_length < 2.0
    - SEVERE: waiting_time_minutes >= 10.0 OR occupancy >= 95% OR queue_length >= 10.0
    - HIGH: waiting_time_minutes >= 5.0 OR occupancy >= 85% OR queue_length >= 5.0
    - MODERATE: default/fallback
    
    Args:
        queue_length: Estimated/predicted queue size.
        capacity: Facility capacity.
        occupied_slots: Current occupied slots.
        waiting_time_minutes: Estimated wait time.
        
    Returns:
        congestion_level (str): "LOW", "MODERATE", "HIGH", "SEVERE"
    """
    queue_length = max(0.0, queue_length)
    waiting_time_minutes = max(0.0, waiting_time_minutes)
    
    if capacity <= 0:
        return "LOW"
        
    occupied_slots = max(0, min(occupied_slots, capacity))
    occupancy_pct = (occupied_slots / capacity) * 100.0
    
    # Classify SEVERE
    if waiting_time_minutes >= 10.0 or occupancy_pct >= 95.0 or queue_length >= 10.0:
        return "SEVERE"
        
    # Classify HIGH
    if waiting_time_minutes >= 5.0 or occupancy_pct >= 85.0 or queue_length >= 5.0:
        return "HIGH"
        
    # Classify LOW
    if waiting_time_minutes < 2.0 and occupancy_pct < 70.0 and queue_length < 2.0:
        return "LOW"
        
    # Default is MODERATE
    return "MODERATE"
