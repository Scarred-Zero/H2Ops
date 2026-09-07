from typing import Callable, Iterable, Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from src.utils.jwt_handler import decode_token, TokenPayload
from src.core.database import (
    session_scope,
)
from src.models.user import User
from sqlalchemy import select

security = HTTPBearer(auto_error=False)


async def _get_token_from_cookie_or_header(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    """
    Prefer Authorization header Bearer token, fallback to HttpOnly cookie 'access_token'.
    """
    if credentials and credentials.scheme.lower() == "bearer":
        return credentials.credentials

    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
    )


async def get_current_user(
    token: str = Depends(_get_token_from_cookie_or_header),
) -> User:
    try:
        payload: TokenPayload = decode_token(token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )

    user_id = payload.sub
    async with session_scope() as session:  # type: AsyncSession
        q = select(User).where(User.id == user_id)
        result = await session.execute(q)
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
            )
        # attach roles from token if needed; prefer DB roles for authoritative checks
        return user


def require_role(allowed_roles: Iterable[str]) -> Callable:
    async def _require_role(user: User = Depends(get_current_user)) -> User:
        user_roles = {
            r.name for r in getattr(user, "roles", [])
        }  # assumes relationship 'roles' exists
        if not set(allowed_roles).intersection(user_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges"
            )
        return user

    return _require_role
