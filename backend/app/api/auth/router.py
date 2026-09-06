"""
FastAPI router definition for Authentication endpoints.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.session import get_async_session
from ...schemas.user import UserCreate, UserLogin, UserResponse, Token
from ...services.auth_service import auth_service
from ...core.dependencies import get_current_user
from ...core.security import create_access_token
from ...models.user import User
from ...core.rate_limiter import RateLimiter

router = APIRouter(prefix="/auth", tags=["Authentication"])
auth_rate_limiter = RateLimiter(requests=5, window_seconds=60)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New User",
    description="Validates input fields, checks for duplicate email, hashes password, and creates user profile.",
    dependencies=[Depends(auth_rate_limiter)]
)
async def register_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_async_session)
) -> UserResponse:
    """
    User registration route.
    """
    user = await auth_service.register_user(db, user_in)
    return user


@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="User Login",
    description="Authenticates user credentials and generates a bearer JWT access token.",
    dependencies=[Depends(auth_rate_limiter)]
)
async def login_user(
    login_in: UserLogin,
    db: AsyncSession = Depends(get_async_session)
) -> Token:
    """
    User authentication / token generation route.
    """
    user = await auth_service.authenticate_user(db, login_in)
    access_token = create_access_token(data={"sub": user.email})
    return Token(access_token=access_token, token_type="bearer")


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Current User Profile",
    description="Protected route returning the caller's user details decoded from the JWT credentials.",
)
async def get_my_profile(
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """
    Caller profile retrieval.
    """
    return current_user
