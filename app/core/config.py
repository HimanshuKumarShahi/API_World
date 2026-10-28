from typing import Optional, Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Project Info
    PROJECT_NAME: str = "FastAPI Modular Auth API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    FRONTEND_URL: str = "http://localhost:3000"

    # Database
    DATABASE_URL: str

    # JWT Security
    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 20
    REFRESH_TOKEN_EXPIRE_DAYS: int = 5
    EMAIL_TOKEN_EXPIRE_MINUTES: int = 20


    # Open-Source Auth Feature Flags

    REQUIRE_EMAIL_VERIFICATION: bool = False

    EMAIL_PROVIDER: Literal["console", "mailtrap", "smtp"] = "console"

    # Optional Email / SMTP -> Won't crash if left empty

    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: str = "APIWorld.auth@gmail.com"
    EMAILS_FROM_NAME: str = "Auth System"

    # jokes
    JOKES_DEFAULT_COUNT: int = 1000


    ENABLED_MODULES: str = "all"

    @property
    def active_modules_list(self) -> list[str]:
        ALL_AVAILABLE = ["auth", "users", "jokes", "banking", "lms", "todos"]
        if self.ENABLED_MODULES.strip().lower() == "all":
            return ALL_AVAILABLE
        
        requested = [
            m.strip().lower() 
            for m in self.ENABLED_MODULES.split(",") 
            if m.strip()
            ]
        seen = set()
        ordered = []
        for m in requested:
            if m in ALL_AVAILABLE and m not in seen:
                seen.add(m)
                ordered.append(m)
        return ordered

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()