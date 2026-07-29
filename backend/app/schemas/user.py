"""
Pydantic schemas for User database representation, registration, login, and updates.
"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr = Field(..., description="User's unique email address")
    full_name: Optional[str] = Field(None, max_length=255, description="User's full name")
    phone: Optional[str] = Field(None, max_length=32, description="User's phone number")
    vehicle_number: Optional[str] = Field(None, max_length=32, description="User's primary vehicle registration number")


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="User's plain password (minimum 8 characters)")


class UserLogin(BaseModel):
    email: EmailStr = Field(..., description="User's registered email address")
    password: str = Field(..., description="User's password")


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=255, description="Update user's full name")
    phone: Optional[str] = Field(None, max_length=32, description="Update user's phone number")
    vehicle_number: Optional[str] = Field(None, max_length=32, description="Update user's primary vehicle number")


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: Optional[str] = None
    email: EmailStr
    phone: Optional[str] = None
    vehicle_number: Optional[str] = None
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None
