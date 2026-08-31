from typing import List
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.session import get_async_session
from ...core.dependencies import get_current_user, get_admin_user
from ...schemas.parking import SlotCreate, SlotUpdate, SlotStatusUpdate, SlotResponse
from ...services.parking_service import parking_service
from ...models.user import User

router = APIRouter(prefix="/slots", tags=["slots"])

@router.get("/{slot_id}", response_model=SlotResponse)
async def get_slot(
    slot_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    slot = await parking_service.get_slot(db, slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    return slot

@router.patch("/{slot_id}", response_model=SlotResponse)
@router.put("/{slot_id}", response_model=SlotResponse)
async def update_slot(
    slot_id: int,
    slot_in: SlotUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_admin_user)
):
    slot = await parking_service.update_slot(db, slot_id, slot_in)
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    return slot

@router.patch("/{slot_id}/status", response_model=SlotResponse)
async def update_slot_status(
    slot_id: int,
    status_in: SlotStatusUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)  # Potentially any user or system can update status
):
    slot = await parking_service.update_slot_status(db, slot_id, status_in.status)
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    return slot

@router.delete("/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_slot(
    slot_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_admin_user)
):
    success = await parking_service.delete_slot(db, slot_id)
    if not success:
        raise HTTPException(status_code=404, detail="Slot not found")
    return None
