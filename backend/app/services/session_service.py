from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from fastapi import HTTPException

from ..models.session import ParkingSession, ParkingSessionStatus
from ..models.reservation import Reservation, ReservationStatus
from ..models.parking_slot import ParkingSlotStatus
from ..models.payment import PaymentMethod
from ..schemas.session import SessionCreate, SessionUpdate
from .parking_service import parking_service
from .reservation_service import reservation_service
from .payment_service import payment_service

class SessionService:
    async def start_session(self, db: AsyncSession, user_id: int, session_in: SessionCreate) -> ParkingSession:
        slot = await parking_service.get_slot(db, session_in.slot_id)
        if not slot:
            raise HTTPException(status_code=404, detail="Slot not found")
        if not slot.is_active:
            raise HTTPException(status_code=400, detail="Slot is not active")

        # If reservation is provided, validate it
        if session_in.reservation_id:
            reservation = await reservation_service.get_reservation(db, session_in.reservation_id)
            if not reservation:
                raise HTTPException(status_code=404, detail="Reservation not found")
            if reservation.user_id != user_id:
                raise HTTPException(status_code=403, detail="Not authorized to use this reservation")
            if reservation.slot_id != session_in.slot_id:
                raise HTTPException(status_code=400, detail="Reservation is for a different slot")
            if reservation.status not in [ReservationStatus.PENDING, ReservationStatus.CONFIRMED]:
                raise HTTPException(status_code=400, detail="Reservation is not valid for starting a session")
            
            # Update reservation status
            reservation.status = ReservationStatus.ACTIVE
            db.add(reservation)
        else:
            # Prevent starting if someone else has it reserved right now
            now = datetime.now(timezone.utc)
            overlap_stmt = select(Reservation).where(
                and_(
                    Reservation.slot_id == session_in.slot_id,
                    Reservation.status.in_([ReservationStatus.PENDING, ReservationStatus.CONFIRMED]),
                    Reservation.reservation_start <= now,
                    Reservation.reservation_end >= now
                )
            )
            overlap = (await db.execute(overlap_stmt)).scalars().first()
            if overlap and overlap.user_id != user_id:
                raise HTTPException(status_code=409, detail="Slot is currently reserved by another user")

        # Check for active session in the slot
        active_session_stmt = select(ParkingSession).where(
            and_(
                ParkingSession.slot_id == session_in.slot_id,
                ParkingSession.status == ParkingSessionStatus.ACTIVE
            )
        )
        active_session = (await db.execute(active_session_stmt)).scalars().first()
        if active_session:
            raise HTTPException(status_code=409, detail="Slot already has an active parking session")
        
        # Check if user already has an active session
        user_active_stmt = select(ParkingSession).where(
            and_(
                ParkingSession.user_id == user_id,
                ParkingSession.status == ParkingSessionStatus.ACTIVE
            )
        )
        user_active = (await db.execute(user_active_stmt)).scalars().first()
        if user_active:
            raise HTTPException(status_code=409, detail="User already has an active parking session")

        now = datetime.now(timezone.utc)
        new_session = ParkingSession(
            user_id=user_id,
            slot_id=session_in.slot_id,
            reservation_id=session_in.reservation_id,
            check_in_time=now,
            status=ParkingSessionStatus.ACTIVE
        )
        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)

        # Update slot status
        await parking_service.update_slot_status(db, slot.id, ParkingSlotStatus.OCCUPIED)

        return new_session

    async def get_session(self, db: AsyncSession, session_id: int) -> Optional[ParkingSession]:
        stmt = select(ParkingSession).where(ParkingSession.id == session_id)
        return (await db.execute(stmt)).scalars().first()

    async def get_active_session(self, db: AsyncSession, user_id: int) -> Optional[ParkingSession]:
        stmt = select(ParkingSession).where(
            and_(
                ParkingSession.user_id == user_id,
                ParkingSession.status == ParkingSessionStatus.ACTIVE
            )
        )
        return (await db.execute(stmt)).scalars().first()

    async def get_user_sessions(self, db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100) -> List[ParkingSession]:
        stmt = select(ParkingSession).where(ParkingSession.user_id == user_id).order_by(ParkingSession.created_at.desc()).offset(skip).limit(limit)
        return list((await db.execute(stmt)).scalars().all())
    
    async def get_all_sessions(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[ParkingSession]:
        stmt = select(ParkingSession).order_by(ParkingSession.created_at.desc()).offset(skip).limit(limit)
        return list((await db.execute(stmt)).scalars().all())

    async def end_session(self, db: AsyncSession, session_id: int, user_id: int, is_admin: bool = False) -> ParkingSession:
        session = await self.get_session(db, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.user_id != user_id and not is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to end this session")
        
        if session.status != ParkingSessionStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Session is not active")

        now = datetime.now(timezone.utc)
        session.check_out_time = now
        session.status = ParkingSessionStatus.COMPLETED

        check_in_time = session.check_in_time.replace(tzinfo=timezone.utc) if session.check_in_time.tzinfo is None else session.check_in_time
        delta = now - check_in_time
        session.duration_minutes = int(delta.total_seconds() / 60)

        # Calculate fee and create payment
        session.fee_amount = payment_service.calculate_fee(session.duration_minutes)
        await payment_service.create_payment(
            db=db,
            session_id=session.id,
            user_id=session.user_id,
            amount=session.fee_amount,
            method=PaymentMethod.ONLINE
        )

        # If there's an associated reservation, mark it completed too
        if session.reservation_id:
            res = await reservation_service.get_reservation(db, session.reservation_id)
            if res and res.status == ReservationStatus.ACTIVE:
                res.status = ReservationStatus.COMPLETED
                db.add(res)

        await db.commit()
        await db.refresh(session)

        # Free the slot (check if someone else has it reserved now, otherwise AVAILABLE)
        active_res_stmt = select(Reservation).where(
            and_(
                Reservation.slot_id == session.slot_id,
                Reservation.status.in_([ReservationStatus.PENDING, ReservationStatus.CONFIRMED]),
                Reservation.reservation_start <= now,
                Reservation.reservation_end >= now
            )
        )
        active_res = (await db.execute(active_res_stmt)).scalars().first()
        if active_res:
            await parking_service.update_slot_status(db, session.slot_id, ParkingSlotStatus.RESERVED)
        else:
            await parking_service.update_slot_status(db, session.slot_id, ParkingSlotStatus.AVAILABLE)

        return session

session_service = SessionService()
