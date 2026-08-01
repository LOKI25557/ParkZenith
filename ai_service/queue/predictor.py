"""
Queue Predictor Module.
Predicts future queue length and trend behavior based on current queue state, arrival/departure rates, and ETA horizon.
"""

import logging

logger = logging.getLogger(__name__)

def predict_future_queue(
    current_queue_length: float,
    arrival_rate_per_hour: float,
    departure_rate_per_hour: float,
    eta_minutes: int,
    capacity: int,
    occupied_slots: int,
) -> tuple[float, float, float, str]:
    """
    Predicts future queue metrics at ETA horizon and determines the queue trend.
    
    Args:
        current_queue_length: Currently estimated queue size.
        arrival_rate_per_hour: Expected hourly arrival rate.
        departure_rate_per_hour: Expected hourly departure rate.
        eta_minutes: Forecast horizon in minutes.
        capacity: Facility capacity.
        occupied_slots: Current occupancy.
        
    Returns:
        tuple containing:
            - predicted_queue_length (float)
            - expected_arrivals during the ETA horizon (float)
            - expected_departures during the ETA horizon (float)
            - queue_trend (str): "DECREASING", "STABLE", "INCREASING", "RAPIDLY_INCREASING"
    """
    current_queue_length = max(0.0, current_queue_length)
    arrival_rate_per_hour = max(0.0, arrival_rate_per_hour)
    departure_rate_per_hour = max(0.0, departure_rate_per_hour)
    eta_minutes = max(0, eta_minutes)
    
    # Calculate arrival/departure rates per minute
    arrival_rate_per_min = arrival_rate_per_hour / 60.0
    departure_rate_per_min = departure_rate_per_hour / 60.0
    
    # Expected arrivals/departures during the ETA interval
    expected_arrivals = arrival_rate_per_min * eta_minutes
    expected_departures = departure_rate_per_min * eta_minutes
    
    # Net growth rate in vehicles per hour
    net_growth_rate_per_hour = arrival_rate_per_hour - departure_rate_per_hour
    
    # Simple fluid model for expected queue length at ETA
    # Queue grows by arrivals and shrinks by departures (or gate service rate, but departures is the bottleneck when full)
    # If the lot is not full, the queue would typically shrink towards 0 at the gate rate.
    # However, to be conservative and general:
    predicted_queue_length = current_queue_length + (expected_arrivals - expected_departures)
    predicted_queue_length = max(0.0, predicted_queue_length)
    
    # If capacity is exceeded, queue continues to build up
    # Clamp to reasonable values
    if not (0.0 <= predicted_queue_length < float('inf')):
        predicted_queue_length = 0.0
        
    # Classify queue trend based on growth rate (vehicles/hour)
    if net_growth_rate_per_hour < -1.0:
        trend = "DECREASING"
    elif net_growth_rate_per_hour <= 1.0:
        trend = "STABLE"
    elif net_growth_rate_per_hour < 5.0:
        trend = "INCREASING"
    else:
        trend = "RAPIDLY_INCREASING"
        
    return (
        float(round(predicted_queue_length, 2)),
        float(round(expected_arrivals, 2)),
        float(round(expected_departures, 2)),
        trend
    )
