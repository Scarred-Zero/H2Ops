import redis.asyncio as aioredis
from fastapi import HTTPException, status
from src.core.config import settings

# Initialize Redis client using your existing Redis container service
redis_client = aioredis.from_url(
    getattr(settings, "REDIS_URL", "redis://redis:6379/0"),
    decode_responses=True,
)


async def check_email_resend_rate_limit(email: str, cooldown_seconds: int = 60) -> None:
    """Enforces a cooldown window on email dispatches to prevent spamming."""
    key = f"rate_limit:resend_email:{email.lower()}"

    # Check if a cooldown lock exists in Redis
    is_locked = await redis_client.get(key)
    if is_locked:
        ttl = await redis_client.ttl(key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Verification email already sent. Please wait {ttl} seconds before requesting another.",
        )

    # Acquire lock with expiration time
    await redis_client.set(key, "1", ex=cooldown_seconds)
