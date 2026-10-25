from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.users.models import User
from app.modules.users.schemas import (
    UserPublicProfile,
    UserPrivateProfile,
    UserUpdateProfile,
)
from app.modules.users.controller import UserController
from app.modules.auth.dependencies import get_current_user

router = APIRouter(prefix="/users", tags=["Users & Profiles"])


# Static /profile routes (Current Authenticated User)
@router.get(
    "/profile",
    response_model=UserPrivateProfile,
    summary="Get current logged-in user details",
)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch(
    "/profile",
    response_model=UserPrivateProfile,
    summary="Update current logged-in user profile",
)
async def update_my_profile(
    data: UserUpdateProfile,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await UserController.update_my_profile(current_user, data, db)


#  Dynamic /profile/{username} route (Public Lookup)
@router.get(
    "/profile/{username}",
    response_model=UserPublicProfile,
    summary="Get public user profile by username",
)
async def get_user_profile_by_username(
    username: str,
    db: AsyncSession = Depends(get_db),
):
    return await UserController.get_profile_by_username(username, db)