from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from fastapi import HTTPException

from ..models.reservation import Reservation, ReservationStatus
from ..models.parking_slot import ParkingSlotStatus
from ..schemas.reservation import ReservationCreate, ReservationUpdate
from .parking_service import parking_service
from .realtime import manager
from ..schemas.realtime import SlotStatusChangedEvent, OccupancyUpdatedEvent, OccupancyData
import asyncio

class ReservationService:
    def __init__(self):
        self._creation_lock = asyncio.Lock()

    async def create_reservation(self, db: AsyncSession, user_id: int, reservation_in: ReservationCreate) -> Reservation:
        async with self._creation_lock:
            # Check slot
            slot = await parking_service.get_slot(db, reservation_in.slot_id)
            if not slot:
                raise HTTPException(status_code=404, detail="Slot not found")
            if not slot.is_active:
                raise HTTPException(status_code=400, detail="Slot is not active")
    
            # Check overlapping
            overlap_stmt = select(Reservation).where(
                and_(
                    Reservation.slot_id == reservation_in.slot_id,
                    Reservation.status.in_([ReservationStatus.PENDING, ReservationStatus.CONFIRMED, ReservationStatus.ACTIVE]),
                    Reservation.reservation_start < reservation_in.reservation_end,
                    Reservation.reservation_end > reservation_in.reservation_start
                )
            ).with_for_update()
            
            try:
                overlaps = (await db.execute(overlap_stmt)).scalars().all()
            except Exception:
                # Fallback if DB (like sqlite) doesn't support with_for_update
                await db.rollback()
                overlap_stmt = overlap_stmt.with_for_update(None)
                overlaps = (await db.execute(overlap_stmt)).scalars().all()
                
            if overlaps:
                raise HTTPException(status_code=409, detail="Slot is already reserved for this time range")
    
            reservation = Reservation(
                user_id=user_id,
                slot_id=reservation_in.slot_id,
                reservation_start=reservation_in.reservation_start,
                reservation_end=reservation_in.reservation_end,
                status=ReservationStatus.CONFIRMED
            )
            db.add(reservation)
            await db.commit()
            await db.refresh(reservation)
    
            # Update slot status to RESERVED if not already
            await parking_service.update_slot_status(db, slot.id, ParkingSlotStatus.RESERVED)
    
            # We can also emit a custom reservation created event if needed, but slot status already broadcasts
    
            return reservation

    async def get_reservation(self, db: AsyncSession, reservation_id: int) -> Optional[Reservation]:
        stmt = select(Reservation).where(Reservation.id == reservation_id)
        return (await db.execute(stmt)).scalars().first()

    async def get_user_reservations(self, db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100) -> List[Reservation]:
        stmt = select(Reservation).where(Reservation.user_id == user_id).offset(skip).limit(limit)
        return list((await db.execute(stmt)).scalars().all())
    
    async def get_all_reservations(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Reservation]:
        stmt = select(Reservation).offset(skip).limit(limit)
        return list((await db.execute(stmt)).scalars().all())

    async def cancel_reservation(self, db: AsyncSession, reservation_id: int, user_id: int, is_admin: bool = False) -> Reservation:
        reservation = await self.get_reservation(db, reservation_id)
        if not reservation:
            raise HTTPException(status_code=404, detail="Reservation not found")
        
        if reservation.user_id != user_id and not is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to cancel this reservation")

        if reservation.status in [ReservationStatus.CANCELLED, ReservationStatus.COMPLETED, ReservationStatus.EXPIRED]:
            raise HTTPException(status_code=400, detail=f"Reservation is already {reservation.status.value}")

        reservation.status = ReservationStatus.CANCELLED
        await db.commit()
        await db.refresh(reservation)

        # Check if there are other active reservations for this slot right now
        # If not, set slot back to AVAILABLE
        now = datetime.now(timezone.utc)
        active_stmt = select(Reservation).where(
            and_(
                Reservation.slot_id == reservation.slot_id,
                Reservation.status.in_([ReservationStatus.PENDING, ReservationStatus.CONFIRMED, ReservationStatus.ACTIVE]),
                Reservation.reservation_start <= now,
                Reservation.reservation_end >= now
            )
        )
        active_reservations = (await db.execute(active_stmt)).scalars().all()
        if not active_reservations:
            await parking_service.update_slot_status(db, reservation.slot_id, ParkingSlotStatus.AVAILABLE)

        return reservation

reservation_service = ReservationService()
