"""
Configurable scoring weights and default facility metadata definitions.
"""

from typing import Dict, Any, Optional
import logging
from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(__name__)


class WeightConfiguration(BaseModel):
    """
    Configuration for recommendation factors weights.
    Validates that all weights are non-negative, between 0.0 and 1.0, and sum to 1.0.
    """
    availability_probability: float = Field(default=0.30, ge=0.0, le=1.0)
    distance: float = Field(default=0.20, ge=0.0, le=1.0)
    forecast_occupancy: float = Field(default=0.15, ge=0.0, le=1.0)
    current_occupancy: float = Field(default=0.10, ge=0.0, le=1.0)
    walking_distance: float = Field(default=0.10, ge=0.0, le=1.0)
    historical_utilization: float = Field(default=0.05, ge=0.0, le=1.0)
    parking_cost: float = Field(default=0.05, ge=0.0, le=1.0)
    queue_congestion: float = Field(default=0.05, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_total_weight(self) -> "WeightConfiguration":
        """
        Ensures that all weights sum to exactly 1.0.
        """
        total = (
            self.availability_probability
            + self.distance
            + self.forecast_occupancy
            + self.current_occupancy
            + self.walking_distance
            + self.historical_utilization
            + self.parking_cost
            + self.queue_congestion
        )
        if not abs(total - 1.0) < 1e-5:
            raise ValueError(f"Weights must sum to 1.0 (got {total:.5f})")
        return self


# Default configuration instance
DEFAULT_WEIGHTS = WeightConfiguration()

# Static registry for facility details to populate metadata for recommendation engine.
# Maps facility_id (str) to metadata attributes.
DEFAULT_FACILITY_REGISTRY: Dict[str, Dict[str, Any]] = {
    "1": {
        "name": "Downtown Central Parking",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "hourly_rate": 20.0,
        "is_active": True,
        "parking_type": "Standard",
        "accessibility": True,
        "queue_wait_minutes": 2,
        "total_slots": 100,
    },
    "2": {
        "name": "City Mall Parking",
        "latitude": 12.9750,
        "longitude": 77.6000,
        "hourly_rate": 40.0,
        "is_active": True,
        "parking_type": "Covered",
        "accessibility": True,
        "queue_wait_minutes": 3,
        "total_slots": 150,
    },
    "FAC-001": {
        "name": "North Station Garage",
        "latitude": 12.9800,
        "longitude": 77.5900,
        "hourly_rate": 15.0,
        "is_active": True,
        "parking_type": "Standard",
        "accessibility": False,
        "queue_wait_minutes": 0,
        "total_slots": 100,
    },
}


def get_facility_metadata(facility_id: str, fallback_lat: float = 12.9716, fallback_lon: float = 77.5946) -> Dict[str, Any]:
    """
    Retrieves facility details from the registry, generating sensible defaults
    if the facility ID is dynamically generated or not registered.
    """
    fid = str(facility_id)
    if fid in DEFAULT_FACILITY_REGISTRY:
        return DEFAULT_FACILITY_REGISTRY[fid]

    logger.warning("Facility '%s' not found in registry. Generating fallback metadata.", fid)
    # Generate deterministic fallback coordinates close to user for testing
    return {
        "name": f"Facility {fid}",
        "latitude": fallback_lat + 0.001,
        "longitude": fallback_lon + 0.001,
        "hourly_rate": 20.0,
        "is_active": True,
        "parking_type": "Standard",
        "accessibility": True,
        "queue_wait_minutes": 0,
        "total_slots": 100,
    }
