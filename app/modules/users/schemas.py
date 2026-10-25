import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserPublicProfile(BaseModel):
    """Returned on GET /api/v1/users/profile/{username}"""
    username: str
    full_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    is_verified: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserPrivateProfile(UserPublicProfile):
    """Returned on GET /api/v1/users/me (for the logged-in user)"""
    id: uuid.UUID
    email: EmailStr
    is_active: bool
    role: str
    updated_at: datetime


class UserUpdateProfile(BaseModel):
    """Used on PATCH /api/v1/users/me to update profile details"""
    full_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = Field(None, max_length=500)