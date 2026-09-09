from datetime import timedelta
from typing import Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
    create_action_token,
    verify_action_token,
)
from src.repositories.user_repo import UserRepository
from src.models.user import User


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Validates user credentials against the database."""
        user = await self.user_repo.get_by_email(email)
        if not user:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        return user

    def create_auth_tokens(self, user: User) -> Dict[str, str]:
        """Generates access and refresh tokens for a authenticated user."""
        role_name = user.role.name.value if user.role else "user"

        access_token = create_access_token(subject=str(user.id), role=role_name)
        refresh_token = create_refresh_token(subject=str(user.id))

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    # ---------------------------------------------------------------------------
    # Email Verification Tokens
    # ---------------------------------------------------------------------------

    def generate_verification_token(self, email: str) -> str:
        """Creates a 12-hour verification token for email confirmation."""
        return create_action_token(
            email=email,
            action="verify_email",
            expires_delta=timedelta(hours=12),
        )

    async def confirm_email_verification(self, token: str) -> Optional[User]:
        """Validates the token and updates user.is_verified = True in DB."""
        email = verify_action_token(token, expected_action="verify_email")
        if not email:
            return None

        user = await self.user_repo.get_by_email(email)
        if not user:
            return None

        # Mark user as verified
        user.is_verified = True
        await self.db.commit()
        await self.db.refresh(user)
        return user

    # ---------------------------------------------------------------------------
    # Password Reset Tokens
    # ---------------------------------------------------------------------------

    def generate_password_reset_token(self, email: str) -> str:
        """Creates a short-lived 1-hour password reset token."""
        return create_action_token(
            email=email,
            action="reset_password",
            expires_delta=timedelta(hours=1),
        )

    async def reset_password_with_token(self, token: str, new_password: str) -> bool:
        """Validates the reset token and updates the user's hashed password."""
        email = verify_action_token(token, expected_action="reset_password")
        if not email:
            return False

        user = await self.user_repo.get_by_email(email)
        if not user:
            return False

        user.hashed_password = hash_password(new_password)
        await self.db.commit()
        return True
