from pathlib import Path

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # Database
    DATABASE_URL: PostgresDsn

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Email (SMTP)
    SMTP_HOST: str
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_PASSWORD: str
    EMAIL_FROM: str

    # Used to build verification/reset links sent in emails
    FRONTEND_URL: str = "http://localhost:5173"

    # Registration rule
    ALLOWED_EMAIL_DOMAIN: str

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", env_file_encoding="utf-8"
    )

    MAX_FILE_SIZE_MB: int = 10
    UPLOAD_DIR: str = "uploads"


settings = Settings() # type: ignore
