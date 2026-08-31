from typing import List
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.session import get_async_session
from ...core.dependencies import get_current_user, get_admin_user
from ...schemas.parking import FacilityCreate, FacilityUpdate, FacilityResponse, AvailabilityResponse
from ...services.parking_service import parking_service
from ...models.user import User

router = APIRouter(prefix="/facilities", tags=["facilities"])

@router.post("", response_model=FacilityResponse, status_code=status.HTTP_201_CREATED)
async def create_facility(
    facility_in: FacilityCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_admin_user)
):
    return await parking_service.create_facility(db, facility_in)

@router.get("", response_model=List[FacilityResponse])
async def get_facilities(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_session)
    # Public route, no auth needed
):
    return await parking_service.get_facilities(db, skip=skip, limit=limit)

@router.get("/{facility_id}", response_model=FacilityResponse)
async def get_facility(
    facility_id: int,
    db: AsyncSession = Depends(get_async_session)
    # Public route
):
    facility = await parking_service.get_facility(db, facility_id)
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")
    return facility

@router.patch("/{facility_id}", response_model=FacilityResponse)
@router.put("/{facility_id}", response_model=FacilityResponse)
async def update_facility(
    facility_id: int,
    facility_in: FacilityUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_admin_user)
):
    facility = await parking_service.update_facility(db, facility_id, facility_in)
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")
    return facility

@router.delete("/{facility_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_facility(
    facility_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_admin_user)
):
    success = await parking_service.delete_facility(db, facility_id)
    if not success:
        raise HTTPException(status_code=404, detail="Facility not found")
    return None

@router.get("/{facility_id}/availability", response_model=AvailabilityResponse)
async def get_facility_availability(
    facility_id: int,
    db: AsyncSession = Depends(get_async_session)
    # Public route
):
    return await parking_service.get_facility_availability(db, facility_id)

from ...schemas.parking import ZoneCreate, ZoneResponse

@router.post("/{facility_id}/zones", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED)
async def create_zone_for_facility(
    facility_id: int,
    zone_in: ZoneCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_admin_user)
):
    return await parking_service.create_zone(db, facility_id, zone_in)

@router.get("/{facility_id}/zones", response_model=List[ZoneResponse])
async def get_zones_for_facility(
    facility_id: int,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_session)
):
    return await parking_service.get_zones_by_facility(db, facility_id, skip=skip, limit=limit)

