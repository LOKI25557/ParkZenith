from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from fastapi import HTTPException, status

from ..models.parking_facility import ParkingFacility
from ..models.parking_zone import ParkingZone
from ..models.parking_slot import ParkingSlot, ParkingSlotStatus
from ..schemas.parking import (
    FacilityCreate, FacilityUpdate, ZoneCreate, ZoneUpdate,
    SlotCreate, SlotUpdate, AvailabilityResponse
)


class ParkingService:
    # ----------------- #
    # FACILITY          #
    # ----------------- #
    async def create_facility(self, db: AsyncSession, facility_in: FacilityCreate) -> ParkingFacility:
        facility = ParkingFacility(**facility_in.model_dump())
        db.add(facility)
        await db.commit()
        await db.refresh(facility)
        return facility

    async def get_facility(self, db: AsyncSession, facility_id: int) -> Optional[ParkingFacility]:
        stmt = select(ParkingFacility).where(ParkingFacility.id == facility_id)
        return (await db.execute(stmt)).scalars().first()

    async def get_facilities(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[ParkingFacility]:
        stmt = select(ParkingFacility).offset(skip).limit(limit)
        return list((await db.execute(stmt)).scalars().all())

    async def update_facility(self, db: AsyncSession, facility_id: int, facility_in: FacilityUpdate) -> Optional[ParkingFacility]:
        facility = await self.get_facility(db, facility_id)
        if not facility:
            return None
        update_data = facility_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(facility, field, value)
        await db.commit()
        await db.refresh(facility)
        return facility

    async def delete_facility(self, db: AsyncSession, facility_id: int) -> bool:
        facility = await self.get_facility(db, facility_id)
        if not facility:
            return False
        await db.delete(facility)
        await db.commit()
        return True

    async def get_facility_availability(self, db: AsyncSession, facility_id: int) -> AvailabilityResponse:
        facility = await self.get_facility(db, facility_id)
        if not facility:
            raise HTTPException(status_code=404, detail="Facility not found")

        from sqlalchemy import case
        stmt_slots = select(
            func.count(ParkingSlot.id).label("total"),
            func.sum(case((ParkingSlot.status == ParkingSlotStatus.AVAILABLE, 1), else_=0)).label("available"),
            func.sum(case((ParkingSlot.status == ParkingSlotStatus.OCCUPIED, 1), else_=0)).label("occupied"),
            func.sum(case((ParkingSlot.status == ParkingSlotStatus.RESERVED, 1), else_=0)).label("reserved")
        ).join(ParkingZone, ParkingZone.id == ParkingSlot.zone_id).where(ParkingZone.facility_id == facility_id)

        result = (await db.execute(stmt_slots)).one()
        total = result.total or 0
        available = result.available or 0
        occupied = result.occupied or 0
        reserved = result.reserved or 0

        occupancy_pct = (occupied / total * 100) if total > 0 else 0.0

        return AvailabilityResponse(
            entity_id=facility_id,
            total_slots=total,
            available=available,
            occupied=occupied,
            reserved=reserved,
            occupancy_percentage=occupancy_pct
        )

    # ----------------- #
    # ZONE              #
    # ----------------- #
    async def create_zone(self, db: AsyncSession, facility_id: int, zone_in: ZoneCreate) -> ParkingZone:
        facility = await self.get_facility(db, facility_id)
        if not facility:
            raise HTTPException(status_code=404, detail="Facility not found")
        zone = ParkingZone(facility_id=facility_id, **zone_in.model_dump())
        try:
            db.add(zone)
            await db.commit()
            await db.refresh(zone)
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=400, detail="Invalid data or duplicate zone name")
        return zone

    async def get_zone(self, db: AsyncSession, zone_id: int) -> Optional[ParkingZone]:
        stmt = select(ParkingZone).where(ParkingZone.id == zone_id)
        return (await db.execute(stmt)).scalars().first()

    async def get_zones_by_facility(self, db: AsyncSession, facility_id: int, skip: int = 0, limit: int = 100) -> List[ParkingZone]:
        stmt = select(ParkingZone).where(ParkingZone.facility_id == facility_id).offset(skip).limit(limit)
        return list((await db.execute(stmt)).scalars().all())

    async def update_zone(self, db: AsyncSession, zone_id: int, zone_in: ZoneUpdate) -> Optional[ParkingZone]:
        zone = await self.get_zone(db, zone_id)
        if not zone:
            return None
        update_data = zone_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(zone, field, value)
        try:
            await db.commit()
            await db.refresh(zone)
        except Exception:
            await db.rollback()
            raise HTTPException(status_code=400, detail="Invalid data")
        return zone

    async def delete_zone(self, db: AsyncSession, zone_id: int) -> bool:
        zone = await self.get_zone(db, zone_id)
        if not zone:
            return False
        await db.delete(zone)
        await db.commit()
        return True

    async def get_zone_availability(self, db: AsyncSession, zone_id: int) -> AvailabilityResponse:
        zone = await self.get_zone(db, zone_id)
        if not zone:
            raise HTTPException(status_code=404, detail="Zone not found")

        from sqlalchemy import case
        stmt_slots = select(
            func.count(ParkingSlot.id).label("total"),
            func.sum(case((ParkingSlot.status == ParkingSlotStatus.AVAILABLE, 1), else_=0)).label("available"),
            func.sum(case((ParkingSlot.status == ParkingSlotStatus.OCCUPIED, 1), else_=0)).label("occupied"),
            func.sum(case((ParkingSlot.status == ParkingSlotStatus.RESERVED, 1), else_=0)).label("reserved")
        ).where(ParkingSlot.zone_id == zone_id)

        result = (await db.execute(stmt_slots)).one()
        total = result.total or 0
        available = result.available or 0
        occupied = result.occupied or 0
        reserved = result.reserved or 0

        occupancy_pct = (occupied / total * 100) if total > 0 else 0.0

        return AvailabilityResponse(
            entity_id=zone_id,
            total_slots=total,
            available=available,
            occupied=occupied,
            reserved=reserved,
            occupancy_percentage=occupancy_pct
        )

    # ----------------- #
    # SLOT              #
    # ----------------- #
    async def create_slot(self, db: AsyncSession, zone_id: int, slot_in: SlotCreate) -> ParkingSlot:
        zone = await self.get_zone(db, zone_id)
        if not zone:
            raise HTTPException(status_code=404, detail="Zone not found")
        slot = ParkingSlot(zone_id=zone_id, **slot_in.model_dump())
        try:
            db.add(slot)
            await db.commit()
            await db.refresh(slot)
        except Exception:
            await db.rollback()
            raise HTTPException(status_code=400, detail="Invalid data or duplicate slot number")
        return slot

    async def get_slot(self, db: AsyncSession, slot_id: int) -> Optional[ParkingSlot]:
        stmt = select(ParkingSlot).where(ParkingSlot.id == slot_id)
        return (await db.execute(stmt)).scalars().first()

    async def get_slots_by_zone(self, db: AsyncSession, zone_id: int, skip: int = 0, limit: int = 100) -> List[ParkingSlot]:
        stmt = select(ParkingSlot).where(ParkingSlot.zone_id == zone_id).offset(skip).limit(limit)
        return list((await db.execute(stmt)).scalars().all())

    async def update_slot(self, db: AsyncSession, slot_id: int, slot_in: SlotUpdate) -> Optional[ParkingSlot]:
        slot = await self.get_slot(db, slot_id)
        if not slot:
            return None
        update_data = slot_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(slot, field, value)
        try:
            await db.commit()
            await db.refresh(slot)
        except Exception:
            await db.rollback()
            raise HTTPException(status_code=400, detail="Invalid data")
        return slot

    async def update_slot_status(self, db: AsyncSession, slot_id: int, status: ParkingSlotStatus) -> Optional[ParkingSlot]:
        slot = await self.get_slot(db, slot_id)
        if not slot:
            return None
        slot.status = status
        await db.commit()
        await db.refresh(slot)
        return slot

    async def delete_slot(self, db: AsyncSession, slot_id: int) -> bool:
        slot = await self.get_slot(db, slot_id)
        if not slot:
            return False
        await db.delete(slot)
        await db.commit()
        return True


parking_service = ParkingService()
