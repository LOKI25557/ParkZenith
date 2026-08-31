from typing import List
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.session import get_async_session
from ...core.dependencies import get_current_user, get_admin_user
from ...schemas.parking import ZoneCreate, ZoneUpdate, ZoneResponse, AvailabilityResponse
from ...services.parking_service import parking_service
from ...models.user import User

router = APIRouter(prefix="/zones", tags=["zones"])

@router.get("/{zone_id}", response_model=ZoneResponse)
async def get_zone(
    zone_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    zone = await parking_service.get_zone(db, zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    return zone

@router.patch("/{zone_id}", response_model=ZoneResponse)
@router.put("/{zone_id}", response_model=ZoneResponse)
async def update_zone(
    zone_id: int,
    zone_in: ZoneUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_admin_user)
):
    zone = await parking_service.update_zone(db, zone_id, zone_in)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    return zone

@router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_zone(
    zone_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_admin_user)
):
    success = await parking_service.delete_zone(db, zone_id)
    if not success:
        raise HTTPException(status_code=404, detail="Zone not found")
    return None

@router.get("/{zone_id}/availability", response_model=AvailabilityResponse)
async def get_zone_availability(
    zone_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    return await parking_service.get_zone_availability(db, zone_id)

from ...schemas.parking import SlotCreate, SlotResponse

@router.post("/{zone_id}/slots", response_model=SlotResponse, status_code=status.HTTP_201_CREATED)
async def create_slot_for_zone(
    zone_id: int,
    slot_in: SlotCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_admin_user)
):
    return await parking_service.create_slot(db, zone_id, slot_in)

@router.get("/{zone_id}/slots", response_model=List[SlotResponse])
async def get_slots_for_zone(
    zone_id: int,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_session)
):
    return await parking_service.get_slots_by_zone(db, zone_id, skip=skip, limit=limit)

