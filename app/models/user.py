from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Email verification (6-digit code — stored as a hash, not plaintext)
    verification_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verification_code_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    verification_attempts: Mapped[int] = mapped_column(Integer, default=0)
    verification_locked_until: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    # Settings
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    theme_preference: Mapped[str] = mapped_column(
        String(10), default="light"
    )  # "light" / "dark"

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
