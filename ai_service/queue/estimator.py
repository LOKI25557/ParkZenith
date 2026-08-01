"""
Queue Estimator Module.
Estimates current queue size and related metrics from facility capacity, occupancy, and traffic rates.
"""

import logging

logger = logging.getLogger(__name__)

def estimate_current_queue(
    capacity: int,
    occupied_slots: int,
    arrival_rate_per_hour: float,
    departure_rate_per_hour: float,
    entry_throughput_per_minute: float = 3.0,
) -> float:
    """
    Estimates the current queue length based on occupancy, capacity, and current flow rates.
    
    Args:
        capacity: Total slots of the facility.
        occupied_slots: Current occupied slots.
        arrival_rate_per_hour: Average arrival rate (vehicles/hour).
        departure_rate_per_hour: Average departure rate (vehicles/hour).
        entry_throughput_per_minute: Entry gate processing rate (vehicles/minute).
        
    Returns:
        Estimated current queue length (non-negative float).
    """
    # Safe checks for inputs
    if capacity <= 0:
        logger.warning("Capacity is zero or negative. Returning zero queue.")
        return 0.0
        
    occupied_slots = max(0, min(occupied_slots, capacity))
    arrival_rate_per_hour = max(0.0, arrival_rate_per_hour)
    departure_rate_per_hour = max(0.0, departure_rate_per_hour)
    entry_throughput_per_minute = max(0.1, entry_throughput_per_minute)  # Prevent division by zero / negative throughput
    
    arrival_rate_per_min = arrival_rate_per_hour / 60.0
    departure_rate_per_min = departure_rate_per_hour / 60.0
    
    occupancy_pct = (occupied_slots / capacity) * 100.0
    
    # 1. Gate bottleneck queue
    # If arrival rate exceeds entry barrier throughput, a queue builds up at the gate
    gate_queue = max(0.0, (arrival_rate_per_min - entry_throughput_per_minute) * 15.0)  # assume 15-min accumulation
    
    # 2. Facility full queue
    # If the facility is nearly or completely full, arriving cars must wait for departures
    full_queue = 0.0
    if occupancy_pct >= 95.0:
        # Lot is virtually full. Accumulation occurs based on net inflow
        full_queue = max(0.0, (arrival_rate_per_min - departure_rate_per_min) * 20.0)
    elif occupancy_pct >= 85.0:
        # Lot is filling up fast. Buffer queue forms
        full_queue = max(0.0, (arrival_rate_per_min - departure_rate_per_min) * 5.0)
        
    estimated_queue = gate_queue + full_queue
    
    # Ensure no NaN or infinity or negative values
    if not (0.0 <= estimated_queue < float('inf')):
        return 0.0
        
    return float(round(estimated_queue, 2))
