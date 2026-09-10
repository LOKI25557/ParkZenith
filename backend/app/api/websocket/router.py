from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
import logging

from ...database.session import get_async_session
from ...services.parking_service import parking_service
from ...services.realtime import manager
from ...schemas.realtime import ParkingSnapshotEvent, ParkingSnapshotData, SlotInfo
from ...models.parking_slot import ParkingSlot
from ...models.parking_zone import ParkingZone
from ...core.security import verify_access_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])

@router.websocket("/parking/{facility_id}")
async def parking_websocket_endpoint(
    websocket: WebSocket, 
    facility_id: int, 
    token: str = None,
    db: AsyncSession = Depends(get_async_session)
):
    if not token or not verify_access_token(token):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized")
        return

    facility = await parking_service.get_facility(db, facility_id)
    if not facility:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Facility not found")
        return
    
    await manager.connect(websocket, facility_id)
    try:
        availability = await parking_service.get_facility_availability(db, facility_id)
        
        stmt = select(ParkingSlot).join(ParkingZone).where(ParkingZone.facility_id == facility_id)
        slots_result = await db.execute(stmt)
        slots = slots_result.scalars().all()
        
        all_slots = [
            SlotInfo(
                id=slot.id,
                slot_number=slot.slot_number,
                zone_id=slot.zone_id,
                status=slot.status.value
            ) for slot in slots
        ]
        
        snapshot_data = ParkingSnapshotData(
            total_slots=availability.total_slots,
            available_slots=availability.available,
            occupied_slots=availability.occupied,
            reserved_slots=availability.reserved,
            occupancy_percentage=availability.occupancy_percentage,
            slots=all_slots
        )
        
        snapshot_event = ParkingSnapshotEvent(
            facility_id=facility_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            data=snapshot_data
        )
        
        await websocket.send_text(snapshot_event.model_dump_json())

        while True:
            # Keep connection open. If the client sends anything, just ignore.
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        await manager.disconnect(websocket, facility_id)
    except Exception as e:
        logger.error(f"WebSocket error for facility {facility_id}: {e}")
        await manager.disconnect(websocket, facility_id)
