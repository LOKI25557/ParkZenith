"""
Estimator module for arrival availability prediction.
Computes occupancy additions, subtractions, and reservation impacts for a target arrival timeframe.
"""

import logging

logger = logging.getLogger(__name__)


def estimate_flow_occupancy_change(
    avg_arrivals_per_hour: float,
    avg_departures_per_hour: float,
    eta_minutes: int
) -> float:
    """
    Estimates the net change in occupancy due to vehicle flow (arrivals - departures) during the ETA window.
    """
    time_fraction_hours = float(eta_minutes) / 60.0
    expected_arrivals = avg_arrivals_per_hour * time_fraction_hours
    expected_departures = avg_departures_per_hour * time_fraction_hours
    
    net_change = expected_arrivals - expected_departures
    logger.debug(
        "Estimated flow change: +%.2f arrivals, -%.2f departures in %d mins. Net: %.2f",
        expected_arrivals, expected_departures, eta_minutes, net_change
    )
    return net_change


def calculate_reservation_impact(
    incoming_reservations: int,
    outgoing_reservations: int
) -> int:
    """
    Computes the net occupancy change from reservations during the ETA window.
    - Incoming reservations increase occupied slots.
    - Outgoing reservations decrease occupied slots.
    """
    impact = incoming_reservations - outgoing_reservations
    logger.debug(
        "Reservation impact: %d incoming, %d outgoing. Net impact: %d",
        incoming_reservations, outgoing_reservations, impact
    )
    return impact
