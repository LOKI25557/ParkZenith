"""
FastAPI router definition for User details and profile updates.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.session import get_async_session
from ..schemas.user import UserUpdate, UserResponse
from ..services.auth_service import auth_service
from ..core.dependencies import get_current_user
from ..models.user import User

router = APIRouter(prefix="/users", tags=["Users Profile"])


@router.put(
    "/profile",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update User Profile",
    description="Protected route allowing the authenticated caller to edit full name, phone, and vehicle number.",
)
async def update_profile(
    update_in: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> UserResponse:
    """
    Updates profile details of the current authenticated user.
    """
    updated_user = await auth_service.update_user_profile(db, current_user, update_in)
    return updated_user
