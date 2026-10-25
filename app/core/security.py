from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_token(
    subject: str | Any,
    token_type: str,
    expires_delta: Optional[timedelta] = None,
    use_refresh_secret: bool = False
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": token_type,
        "iat": datetime.now(timezone.utc)
    }
    secret = settings.JWT_REFRESH_SECRET_KEY if use_refresh_secret else settings.JWT_SECRET_KEY
    return jwt.encode(to_encode, secret, algorithm=settings.JWT_ALGORITHM)


def create_access_token(subject: str | Any) -> str:
    return create_token(
        subject=subject,
        token_type="access",
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )


def create_refresh_token(subject: str | Any) -> str:
    return create_token(
        subject=subject,
        token_type="refresh",
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        use_refresh_secret=True
    )


def create_email_verification_token(subject: str | Any) -> str:
    return create_token(
        subject=subject,
        token_type="verify_email",
        expires_delta=timedelta(minutes=settings.EMAIL_TOKEN_EXPIRE_MINUTES)
    )


def create_password_reset_token(subject: str | Any) -> str:
    return create_token(
        subject=subject,
        token_type="reset_password",
        expires_delta=timedelta(minutes=settings.EMAIL_TOKEN_EXPIRE_MINUTES)
    )


def decode_token(token: str, expected_type: str, is_refresh: bool = False) -> Optional[str]:
    """
    Decodes a JWT, verifies its signature, expiration, and ensures the 'type' matches.
    Returns the 'sub' (user_id or email) if valid, else None.
    """
    secret = settings.JWT_REFRESH_SECRET_KEY if is_refresh else settings.JWT_SECRET_KEY
    try:
        payload = jwt.decode(token, secret, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != expected_type:
            return None
        return payload.get("sub")
    except JWTError:
        return None