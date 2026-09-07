from datetime import datetime, timedelta, timezone
from typing import TypedDict, Optional
import jwt

from pydantic import BaseModel, Field
from src.core.config import settings

ALGORITHM = settings.JWT_ALGORITHM
SECRET = settings.JWT_SECRET
ACCESS_TOKEN_EXPIRES_MINUTES = settings.JWT_ACCESS_TOKEN_MINUTES


class TokenPayload(BaseModel):
    sub: str = Field(..., description="Subject (user id)")
    roles: list[str] = Field(default_factory=list)
    exp: Optional[int] = None


def create_access_token(
    subject: str, roles: list[str], expires_delta: Optional[timedelta] = None
) -> str:
    now = datetime.now(timezone.utc)
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRES_MINUTES)
    exp = now + expires_delta
    payload = {
        "sub": subject,
        "roles": roles,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    token = jwt.encode(payload, SECRET, algorithm=ALGORITHM)
    return token


def decode_token(token: str) -> TokenPayload:
    try:
        data = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        payload = TokenPayload(**data)
        return payload
    except jwt.ExpiredSignatureError as exc:
        raise jwt.ExpiredSignatureError("Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise jwt.InvalidTokenError("Invalid token") from exc
