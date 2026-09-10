from enum import Enum

class RealtimeEventType(str, Enum):
    PARKING_SNAPSHOT = "parking_snapshot"
    SLOT_STATUS_CHANGED = "slot_status_changed"
    OCCUPANCY_UPDATED = "occupancy_updated"
