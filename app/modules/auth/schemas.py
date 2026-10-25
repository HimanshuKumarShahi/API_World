from pydantic import BaseModel, EmailStr, Field, field_validator

RESERVED_USERNAMES = {"profile", "me", "admin", "auth", "login", "register", "logout", "settings", "root"}

class RegisterRequest(BaseModel):
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern="^[a-zA-Z0-9_]+$",
        description="Alphanumeric username with underscores only"
    )
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str | None = Field(None, max_length=100)

    @field_validator("username")
    @classmethod
    def prevent_reserved_usernames(cls, v: str) -> str:
        if v.lower() in RESERVED_USERNAMES:
            raise ValueError(f"Username '{v}' is reserved and cannot be used.")
        return v.lower()


class LoginRequest(BaseModel):
    email_or_username: str = Field(..., description="Enter either your email or username")
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshOrLogoutRequest(BaseModel):
    refresh_token: str


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)


class MessageResponse(BaseModel):
    message: str