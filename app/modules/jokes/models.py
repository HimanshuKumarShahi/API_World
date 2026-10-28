from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Integer, String, Boolean, Text, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Joke(Base):
    __tablename__ = "jokes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)

    category: Mapped[str] = mapped_column(String(30), nullable=False, index=True)

    joke_type: Mapped[str] = mapped_column(String(15), nullable=False, default="twopart", index=True)

    setup: Mapped[str] = mapped_column(Text, nullable=False)
    delivery: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    is_dark: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    is_adult: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    
    safe_mode: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    likes_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dislikes_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_jokes_taste_filter", "category", "safe_mode", "is_dark", "is_adult"),
    )