import uuid
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, update

from app.core.config import settings

from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    create_email_verification_token,
    create_password_reset_token,
    decode_token,
)
from app.common.email import send_verification_email, send_reset_password_email
from app.modules.users.models import User
from app.modules.auth.models import RefreshToken
from app.modules.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    ResetPasswordRequest,
)


class AuthController:

    @staticmethod
    async def register_user(
        data: RegisterRequest,
        background_tasks: BackgroundTasks,
        db: AsyncSession,
    ) -> dict:
        #  Check if email or username already exists
        stmt = select(User).where(
            or_(
                User.email == data.email.lower(),
                User.username == data.username.lower(),
            )
        )
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            if existing_user.email == data.email.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email is already registered",
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username is already taken",
            )

        #  Create new user with hashed password
        new_user = User(
            username=data.username.lower(),
            email=data.email.lower(),
            hashed_password=get_password_hash(data.password),
            full_name=data.full_name,
            is_verified=False,
            is_active=True,
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        #  Generate email verification token & dispatch email in background
        verify_token = create_email_verification_token(subject=str(new_user.id))
        background_tasks.add_task(
            send_verification_email, new_user.email, verify_token
        )

        return {
            "message": "Registration successful. Please check your email (or console logs) to verify your account."
        }

    @staticmethod
    async def verify_email(token: str, db: AsyncSession) -> dict:
        user_id_str = decode_token(token, expected_type="verify_email")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token",
            )

        result = await db.execute(
            select(User).where(User.id == uuid.UUID(user_id_str))
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if user.is_verified:
            return {"message": "Email is already verified."}

        user.is_verified = True
        await db.commit()
        return {"message": "Email verified successfully. You can now log in."}


    @staticmethod
    async def login_user(data: LoginRequest, db: AsyncSession) -> TokenResponse:
        # Lookup user by email OR username
        identifier = data.email_or_username.lower()
        stmt = select(User).where(
            or_(User.email == identifier, User.username == identifier)
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not verify_password(data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email/username or password",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated",
            )

        if not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Please verify your email address before logging in",
            )

        #  Generate Access & Refresh tokens
        access_token = create_access_token(subject=str(user.id))
        refresh_token_str = create_refresh_token(subject=str(user.id))

        #  Store Refresh Token in PostgreSQL for session tracking/revocation
        db_refresh_token = RefreshToken(
            user_id=user.id,
            token=refresh_token_str,
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        db.add(db_refresh_token)
        await db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_str,
        )


    @staticmethod
    async def refresh_access_token(
        refresh_token: str, db: AsyncSession
    ) -> TokenResponse:
        user_id_str = decode_token(
            refresh_token, expected_type="refresh", is_refresh=True
        )
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        # Check if token exists in DB and is not revoked
        stmt = select(RefreshToken).where(
            RefreshToken.token == refresh_token,
            RefreshToken.is_revoked.is_(False),
        )
        result = await db.execute(stmt)
        stored_token = result.scalar_one_or_none()

        if not stored_token or stored_token.expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked or expired",
            )

        # Rotate token: revoke old one and issue new pair
        stored_token.is_revoked = True
        new_access = create_access_token(subject=user_id_str)
        new_refresh = create_refresh_token(subject=user_id_str)

        db.add(
            RefreshToken(
                user_id=uuid.UUID(user_id_str),
                token=new_refresh,
                expires_at=datetime.now(timezone.utc)
                + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            )
        )
        await db.commit()

        return TokenResponse(access_token=new_access, refresh_token=new_refresh)



    @staticmethod
    async def logout_user(refresh_token: str, db: AsyncSession) -> dict:
        stmt = select(RefreshToken).where(RefreshToken.token == refresh_token)
        result = await db.execute(stmt)
        stored_token = result.scalar_one_or_none()

        if stored_token and not stored_token.is_revoked:
            stored_token.is_revoked = True
            await db.commit()

        return {"message": "Logged out successfully."}

    @staticmethod
    async def forgot_password(
        email: str, background_tasks: BackgroundTasks, db: AsyncSession
    ) -> dict:
        stmt = select(User).where(User.email == email.lower())
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        # Always return 200 OK even if email isn't found to prevent user enumeration
        if user and user.is_active:
            reset_token = create_password_reset_token(subject=str(user.id))
            background_tasks.add_task(
                send_reset_password_email, user.email, reset_token
            )

        return {
            "message": "If that email is registered, a password reset link has been sent."
        }


    @staticmethod
    async def reset_password(
        data: ResetPasswordRequest, db: AsyncSession
    ) -> dict:
        user_id_str = decode_token(data.token, expected_type="reset_password")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired password reset token",
            )

        user_uuid = uuid.UUID(user_id_str)
        result = await db.execute(select(User).where(User.id == user_uuid))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Update password hash
        user.hashed_password = get_password_hash(data.new_password)

        # Revoke all active refresh tokens for this user across all devices
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_uuid)
            .values(is_revoked=True)
        )

        await db.commit()
        return {"message": "Password has been reset successfully. Please log in with your new password."}