"""
Queue Waiting Time Estimator.
Estimates the wait time in minutes for a vehicle to enter the parking facility.
"""

import logging

logger = logging.getLogger(__name__)

def estimate_waiting_time(
    queue_length: float,
    capacity: int,
    occupied_slots: int,
    departure_rate_per_hour: float,
    entry_throughput_per_minute: float = 3.0,
) -> float:
    """
    Estimates expected waiting time in minutes to enter the facility.
    
    Args:
        queue_length: Estimated queue length.
        capacity: Total facility capacity.
        occupied_slots: Current occupied slots.
        departure_rate_per_hour: Expected hourly departures.
        entry_throughput_per_minute: Service rate of the entry gate (vehicles/min).
        
    Returns:
        Estimated waiting time in minutes (non-negative float).
    """
    queue_length = max(0.0, queue_length)
    if queue_length == 0.0:
        return 0.0
        
    if capacity <= 0:
        return 0.0
        
    occupied_slots = max(0, min(occupied_slots, capacity))
    available_slots = max(0, capacity - occupied_slots)
    entry_throughput_per_minute = max(0.1, entry_throughput_per_minute)
    
    # Calculate departure rate per minute
    # Fallback to at least 2.0 departures per hour (0.033 per minute) if lot is full, to avoid infinite waits
    min_departure_rate = max(2.0, capacity * 0.02)  # at least 2% of capacity per hour
    effective_dep_rate_per_hour = max(min_departure_rate, departure_rate_per_hour)
    departure_rate_per_min = effective_dep_rate_per_hour / 60.0
    
    # Wait time calculation
    if available_slots >= queue_length:
        # All cars can park, bottleneck is just entry gate throughput
        wait_time = queue_length / entry_throughput_per_minute
    else:
        # Some cars must wait for departures
        gate_wait = available_slots / entry_throughput_per_minute
        remaining_queue = queue_length - available_slots
        dep_wait = remaining_queue / departure_rate_per_min
        wait_time = gate_wait + dep_wait
        
    # Clamp and validate output
    if not (0.0 <= wait_time < float('inf')):
        return 0.0
        
    return float(round(wait_time, 2))
