from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from src.core.config import settings

# ---------------------------------------------------------------------------
# Password Hashing & Verification
# ---------------------------------------------------------------------------


def hash_password(password: str) -> str:
    """Hashes a plain text password using bcrypt, enforcing the 72-byte limit."""
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain text password against a hashed password."""
    pwd_bytes = plain_password.encode("utf-8")[:72]
    hash_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(pwd_bytes, hash_bytes)


# ---------------------------------------------------------------------------
# Token Generation (Auth & Action Tokens)
# ---------------------------------------------------------------------------


def create_access_token(subject: str, role: str) -> str:
    """Creates a short-lived OAuth2 access token for user authentication."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": subject, "role": role, "exp": expire, "type": "access"}
    return jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def create_refresh_token(subject: str) -> str:
    """Creates a long-lived refresh token."""
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {"sub": subject, "exp": expire, "type": "refresh"}
    return jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def create_action_token(email: str, action: str, expires_delta: timedelta) -> str:
    """Creates a time-bound token for single actions (e.g. 'verify_email', 'reset_password')."""
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {"sub": email, "action": action, "exp": expire}
    return jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


# ---------------------------------------------------------------------------
# Token Decoding & Validation
# ---------------------------------------------------------------------------


def decode_token(token: str) -> dict:
    """Decodes a JWT token and returns its payload dict, or an empty dict if invalid."""
    try:
        return jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError:
        return {}


def verify_action_token(token: str, expected_action: str) -> Optional[str]:
    """
    Decodes an action token, validates the intended action type, and returns the email subject.
    Returns None if the token is invalid, expired, or action type mismatches.
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        email: Optional[str] = payload.get("sub")
        action: Optional[str] = payload.get("action")

        if not email or action != expected_action:
            return None

        return email
    except JWTError:
        return None
