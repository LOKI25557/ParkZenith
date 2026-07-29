"""
Authentication Service managing user registration, authentication, and profile updates.
"""

import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status

from ..models.user import User
from ..schemas.user import UserCreate, UserLogin, UserUpdate
from ..core.security import hash_password, verify_password

logger = logging.getLogger(__name__)


class AuthService:
    """
    Service coordinating authentication logic and database transactions.
    """

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        """
        Retrieves a user record by email address.
        """
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def register_user(self, db: AsyncSession, user_in: UserCreate) -> User:
        """
        Registers a new user after verifying that the email is unique.
        """
        logger.info("Attempting to register user with email: %s", user_in.email)
        existing_user = await self.get_user_by_email(db, user_in.email)
        if existing_user:
            logger.warning("Registration failed. Email already registered: %s", user_in.email)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered"
            )

        # Hash password and create database user record
        hashed = hash_password(user_in.password)
        db_user = User(
            email=user_in.email,
            full_name=user_in.full_name,
            phone=user_in.phone,
            vehicle_number=user_in.vehicle_number,
            password_hash=hashed,
            is_active=True
        )
        
        db.add(db_user)
        try:
            await db.commit()
            await db.refresh(db_user)
            logger.info("Successfully registered user id: %d", db_user.id)
            return db_user
        except Exception as e:
            await db.rollback()
            logger.exception("Database error occurred during user registration: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An internal server error occurred while creating user"
            )

    async def authenticate_user(self, db: AsyncSession, login_in: UserLogin) -> User:
        """
        Authenticates a user by email and password, returning the user model.
        Raises 401 if credentials are invalid or user is inactive.
        """
        user = await self.get_user_by_email(db, login_in.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not verify_password(login_in.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated"
            )

        return user

    async def update_user_profile(self, db: AsyncSession, user: User, update_in: UserUpdate) -> User:
        """
        Updates the profile parameters of the current user.
        """
        logger.info("Updating profile details for user id: %d", user.id)
        
        if update_in.full_name is not None:
            user.full_name = update_in.full_name
        if update_in.phone is not None:
            user.phone = update_in.phone
        if update_in.vehicle_number is not None:
            user.vehicle_number = update_in.vehicle_number

        try:
            db.add(user)
            await db.commit()
            await db.refresh(user)
            logger.info("Successfully updated profile for user id: %d", user.id)
            return user
        except Exception as e:
            await db.rollback()
            logger.exception("Database error during profile update: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user profile"
            )


auth_service = AuthService()
