import jwt
import secrets
from datetime import datetime, timedelta, timezone

from pwdlib import PasswordHash

from app.core.config import settings

password_hash = PasswordHash.recommended()


# --- Password hashing ---


def hash_password(plain_password: str) -> str:
    return password_hash.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


# --- Login access token (used after successful login) ---


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire, "purpose": "access"})
    return jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def decode_token(token: str) -> dict:
    return jwt.decode(
        token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )


# --- Short-lived tokens for email verification & password reset ---
# These carry a "purpose" claim so a verification link can't be reused as a login token, etc.


def create_purpose_token(user_id: int, purpose: str, expire_minutes: int = 30) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    payload = {"user_id": user_id, "purpose": purpose, "exp": expire}
    return jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def verify_purpose_token(token: str, expected_purpose: str) -> int:
    """Decodes the token and returns user_id if valid and purpose matches, else raises jwt exceptions."""
    payload = jwt.decode(
        token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )
    if payload.get("purpose") != expected_purpose:
        raise jwt.InvalidTokenError("Token purpose mismatch")
    return payload["user_id"]


def generate_verification_code() -> str:
    """Generates a random 6-digit numeric code as a string, e.g. '042817'."""
    return f"{secrets.randbelow(1_000_000):06d}"
