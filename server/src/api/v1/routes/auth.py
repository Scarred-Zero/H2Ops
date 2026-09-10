from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.src.models.role import Role
from src.schemas.auth import LoginRequest, RegisterRequest, RegisterResponse, TokenResponse
from src.schemas.auth import ForgotPasswordRequest, ResetPasswordRequest

from src.services.auth_service import AuthService
from src.services.mail_service import MailService
from src.core.security import hash_password
from src.utils.rate_limiter import check_email_resend_rate_limit
from src.models.user import User
from src.models.role import UserRole 
from src.core.database import get_db
from src.dependencies.auth import get_current_user

router = APIRouter()

@router.get("/me", response_model=dict)
async def me(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "full_name": current_user.full_name,
        "roles": [r.name for r in getattr(current_user, "roles", [])],
    }


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check if user already exists
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    # Map frontend role string to the UserRole Enum securely
    role_mapping = {
        "compliance_auditor": UserRole.COMPLIANCE_AUDITOR,
        "facility_admin": UserRole.FACILITY_ADMIN,
        "plant_operator": UserRole.PLANT_OPERATOR,
    }
    requested_role = (payload.role or "plant_operator").lower()
    target_role_enum = role_mapping.get(requested_role, UserRole.PLANT_OPERATOR)

    # Grab the corresponding Role database entry
    role_res = await db.execute(select(Role).where(Role.name == target_role_enum))
    user_role = role_res.scalar_one_or_none()

    if not user_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Role configuration for '{target_role_enum.value}' is missing from the database.",
        )

    # Ensure Operators are attached to an active water treatment site
    if target_role_enum == UserRole.PLANT_OPERATOR or target_role_enum == UserRole.FACILITY_ADMIN and not payload.facility_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plant Operators and Facility Admins must be assigned to a specific facility_id upon registration.",
        )

    # Construct the user
    new_user = User(
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role_id=user_role.id,
        facility_id=(
            payload.facility_id
            if target_role_enum != UserRole.COMPLIANCE_AUDITOR
            else None
        ),
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user, attribute_names=["role"])

    # Generate token and dispatch verification email
    auth_svc = AuthService(db)
    token = auth_svc.generate_verification_token(new_user.email)
    MailService.send_verification_email(new_user.email, token)

    return new_user


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    """
    Authenticate user and set HttpOnly cookie with access token.
    """
    if not payload.email or not payload.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or password",
        )

    auth_svc = AuthService(db)
    user = await auth_svc.authenticate_user(payload.email, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Resend email and block login if account is unverified
    if not user.is_verified:
        await check_email_resend_rate_limit(user.email, cooldown_seconds=60)
        token = auth_svc.generate_verification_token(user.email)
        MailService.send_verification_email(user.email, token)

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. A new verification link has been sent to your email address.",
        )

    # Generate tokens
    tokens = auth_svc.create_auth_tokens(user)

    # Set HttpOnly cookie
    response.set_cookie(
        key="access_token",
        value=tokens['access_token'],
        httponly=True,
        samesite="lax",
        secure=False, # Set to True in production with HTTPS
    )
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        samesite="lax",
        secure=False,  # Set to True in production (HTTPS)
    )

    return {"message": "Login Successful"}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")
    return {"message": "Logged out successfully"}


# Account Recovery & Verification Endpoints
@router.get("/verify-email")
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    """Verifies the token from the email link and activates the user account."""
    auth_svc = AuthService(db)
    user = await auth_svc.confirm_email_verification(token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification link.",
        )

    return {"message": "Email successfully verified."}


@router.post("/forgot-password")
async def forgot_password(
    payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)
):
    """Generates a password reset token and sends it via email."""
    auth_svc = AuthService(db)

    # Use the repository directly to check if the user exists
    user = await auth_svc.user_repo.get_by_email(payload.email)

    if user:
        token = auth_svc.generate_password_reset_token(user.email)
        MailService.send_password_reset_email(user.email, token)

    return {
        "message": "If an account exists with that email, a password reset link has been sent."
    }


@router.post("/reset-password")
async def reset_password(
    payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)
):
    """Validates the reset token and updates the user's password."""
    auth_svc = AuthService(db)
    success = await auth_svc.reset_password_with_token(
        payload.token, payload.new_password
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset link.",
        )

    return {"message": "Password successfully reset."}
