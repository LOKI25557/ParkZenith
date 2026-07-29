"""
FastAPI dependencies for extracting and verifying JWT credentials and users.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.session import get_async_session
from ..services.auth_service import auth_service
from ..core.security import verify_access_token
from ..models.user import User

# HTTPBearer parser (auto_error=False to customize response/errors manually)
security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_async_session),
) -> User:
    """
    Dependency checking the request authorization header for a valid bearer JWT.
    Validates token expiration, signature, and fetches the corresponding User object.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials/token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    email = verify_access_token(token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await auth_service.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with this token could not be found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account has been deactivated"
        )

    return user
