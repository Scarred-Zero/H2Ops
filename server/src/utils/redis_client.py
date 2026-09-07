from __future__ import annotations

from typing import Optional
import logging
import os

from redis.asyncio import Redis
from src.core.config import settings

logger = logging.getLogger("h2ops.redis")

_redis_client: Optional[Redis] = None


def get_redis() -> Optional[Redis]:
    """
    Return the global Redis client if initialized, otherwise None.
    Call init_redis(...) during app startup.
    """
    return _redis_client


def init_redis(url: Optional[str] = None, *, decode_responses: bool = False) -> Redis:
    """
    Initialize the global Redis client. Safe to call multiple times (idempotent).
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    redis_url = url or settings.REDIS_URL
    client = Redis.from_url(redis_url, decode_responses=decode_responses)
    _redis_client = client
    logger.info("Initialized Redis client for %s", redis_url)
    return _redis_client


async def close_redis() -> None:
    """
    Close the global Redis client connection pool.
    """
    global _redis_client
    if _redis_client is None:
        return
    try:
        await _redis_client.close()
        await _redis_client.connection_pool.disconnect()
        logger.info("Closed Redis client")
    except Exception:
        logger.exception("Error while closing Redis client")
    finally:
        _redis_client = None
