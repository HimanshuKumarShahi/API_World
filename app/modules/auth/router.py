from fastapi import APIRouter, Depends, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshOrLogoutRequest,
    VerifyEmailRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    MessageResponse,
)
from app.modules.auth.controller import AuthController

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    data: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    return await AuthController.register_user(data, background_tasks, db)


@router.post(
    "/verify-email",
    response_model=MessageResponse,
    summary="Verify email address using token",
)
async def verify_email(
    data: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
):
    return await AuthController.verify_email(data.token, db)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with email or username",
)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    return await AuthController.login_user(data, db)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate refresh token and get new access token",
)
async def refresh_token(
    data: RefreshOrLogoutRequest,
    db: AsyncSession = Depends(get_db),
):
    return await AuthController.refresh_access_token(data.refresh_token, db)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout and revoke refresh token",
)
async def logout(
    data: RefreshOrLogoutRequest,
    db: AsyncSession = Depends(get_db),
):
    return await AuthController.logout_user(data.refresh_token, db)


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request a password reset email",
)
async def forgot_password(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    return await AuthController.forgot_password(data.email, background_tasks, db)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password using reset token",
)
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    return await AuthController.reset_password(data, db)