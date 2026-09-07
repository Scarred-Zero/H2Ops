# server/src/api/v1/routes/auth.py
from __future__ import annotations

from typing import Any
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.auth import LoginRequest, TokenResponse
from src.utils.jwt_handler import create_access_token
from src.core.database import async_session
from src.models.user import User  # adapt to your User model
from src.core.security import verify_password  # adapt to your password verify util
from src.core.config import settings

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, response: Response) -> Any:
    """
    Authenticate user and set HttpOnly cookie with access token.
    """
    async with async_session() as session:  # type: AsyncSession
        q = select(User).where(User.username == payload.username)
        result = await session.execute(q)
        user = result.scalar_one_or_none()
        if user is None or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )

    roles = [r.name for r in getattr(user, "roles", [])]
    token = create_access_token(
        subject=str(user.id),
        roles=roles,
        expires_delta=timedelta(minutes=settings.jwt_access_token_minutes),
    )

    # Set HttpOnly cookie
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.jwt_access_token_minutes * 60,
        path="/",
    )

    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout")
async def logout(response: Response) -> Any:
    response.delete_cookie("access_token", path="/")
    return {"detail": "logged out"}
