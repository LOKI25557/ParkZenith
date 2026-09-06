from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_current_user, get_admin_user
from ...database.session import get_async_session
from ...models.user import User
from ...schemas.reservation import ReservationCreate, ReservationRead, ReservationListResponse
from ...services.reservation_service import reservation_service
from ...core.rate_limiter import RateLimiter

router = APIRouter(prefix="/reservations", tags=["reservations"])
reservation_rate_limiter = RateLimiter(requests=10, window_seconds=60)

@router.post("", response_model=ReservationRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(reservation_rate_limiter)])
async def create_reservation(
    reservation_in: ReservationCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    return await reservation_service.create_reservation(db, current_user.id, reservation_in)

@router.get("", response_model=ReservationListResponse)
async def get_reservations(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    if current_user.is_superuser:
        items = await reservation_service.get_all_reservations(db, skip=skip, limit=limit)
    else:
        items = await reservation_service.get_user_reservations(db, current_user.id, skip=skip, limit=limit)
    return {"items": items, "total": len(items)}

@router.delete("/{reservation_id}", response_model=ReservationRead)
async def cancel_reservation(
    reservation_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    return await reservation_service.cancel_reservation(db, reservation_id, current_user.id, is_admin=current_user.is_superuser)
