from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.modules.users.models import User
from app.modules.users.schemas import UserUpdateProfile


class UserController:

    @staticmethod
    async def get_profile_by_username(username: str, db: AsyncSession) -> User:
        stmt = select(User).where(
            User.username == username.lower(),
            User.is_active.is_(True),
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '@{username}' not found",
            )
        return user


    @staticmethod
    async def update_my_profile(
        current_user: User,
        data: UserUpdateProfile,
        db: AsyncSession,
    ) -> User:
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(current_user, field, value)

        await db.commit()
        await db.refresh(current_user)
        return current_user