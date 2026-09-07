# server/src/repositories/telemetry_repo.py
from __future__ import annotations

from typing import Any, Dict, Optional
import json
import logging

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import async_session
from src.models.alert import Alert
from src.utils.redis_client import get_redis

logger = logging.getLogger("h2ops.telemetry_repo")


class TelemetryRepository:
    @staticmethod
    async def create_alert(alert_payload: Dict[str, Any]) -> Alert:
        """
        Persist an alert into the alerts table and optionally publish to Redis channel.
        Returns the created Alert ORM instance.
        """
        async with async_session() as session:  # type: AsyncSession
            async with session.begin():
                stmt = (
                    insert(Alert)
                    .values(
                        device_id=alert_payload["device_id"],
                        payload=alert_payload,
                    )
                    .returning(Alert)
                )
                result = await session.execute(stmt)
                created_row = result.scalar_one()
                # SQLAlchemy returns a mapped instance when returning the model
                # but depending on DB driver you might get a Row; ensure we have an ORM object
                # If scalar_one() returns a Row, fetch by id:
                if not isinstance(created_row, Alert):
                    # fallback: query by id
                    alert_id = created_row.id  # type: ignore[attr-defined]
                    q = select(Alert).where(Alert.id == alert_id)
                    res = await session.execute(q)
                    created_row = res.scalar_one()

            # publish to redis channel for real-time consumers (optional)
            try:
                redis = get_redis()
                if redis:
                    channel = "alerts"
                    await redis.publish(channel, json.dumps(alert_payload))
            except Exception:
                logger.exception("Failed to publish alert to redis")

            return created_row

    @staticmethod
    async def list_alerts_for_device(
        device_id: str, limit: int = 100
    ) -> list[Dict[str, Any]]:
        async with async_session() as session:
            q = (
                select(Alert)
                .where(Alert.device_id == device_id)
                .order_by(Alert.created_at.desc())
                .limit(limit)
            )
            result = await session.execute(q)
            rows = result.scalars().all()
            return [r.payload for r in rows]
