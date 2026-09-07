from typing import Any, Dict, Optional
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import async_session
from src.models.device import Device
from src.repositories.telemetry_repo import TelemetryRepository
from src.core.redis_client import redis_client  # optional; adapt if not present

logger = logging.getLogger("h2ops.telemetry")


async def _get_device_thresholds(device_id: str) -> Dict[str, Any]:
    """
    Fetch thresholds for a device. Try Redis cache first, fallback to DB.
    """
    cache_key = f"device:{device_id}:thresholds"
    try:
        if redis_client:
            cached = await redis_client.get(cache_key)
            if cached:
                # redis returns bytes; decode and parse JSON
                import json

                return json.loads(cached)
    except Exception:
        logger.debug(
            "Redis unavailable or error reading thresholds cache", exc_info=True
        )

    async with async_session() as session:  # type: AsyncSession
        q = select(Device.thresholds).where(Device.id == device_id)
        result = await session.execute(q)
        thresholds = result.scalar_one_or_none() or {}
        # prime cache
        try:
            if redis_client:
                import json

                await redis_client.set(cache_key, json.dumps(thresholds), ex=300)
        except Exception:
            logger.debug("Failed to set thresholds cache", exc_info=True)
        return thresholds


async def evaluate_telemetry(
    device_id: str, payload: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Evaluate telemetry payload against device thresholds.
    Returns an alert dict if any threshold is violated, otherwise None.
    payload example: {"ph": 8.2, "turbidity": 3.4, "orp": 250}
    """
    thresholds = await _get_device_thresholds(device_id)

    alerts = []

    ph = payload.get("ph")
    if ph is not None:
        ph_min = thresholds.get("ph_min")
        ph_max = thresholds.get("ph_max")
        if ph_min is not None and ph < ph_min:
            alerts.append(
                {"metric": "ph", "value": ph, "threshold": ph_min, "type": "below"}
            )
        if ph_max is not None and ph > ph_max:
            alerts.append(
                {"metric": "ph", "value": ph, "threshold": ph_max, "type": "above"}
            )

    turbidity = payload.get("turbidity")
    if turbidity is not None:
        turbidity_max = thresholds.get("turbidity_max_ntu")
        if turbidity_max is not None and turbidity > turbidity_max:
            alerts.append(
                {
                    "metric": "turbidity",
                    "value": turbidity,
                    "threshold": turbidity_max,
                    "type": "above",
                }
            )

    orp = payload.get("orp")
    if orp is not None:
        orp_min = thresholds.get("orp_min_mv")
        if orp_min is not None and orp < orp_min:
            alerts.append(
                {"metric": "orp", "value": orp, "threshold": orp_min, "type": "below"}
            )

    if alerts:
        alert_payload = {
            "device_id": device_id,
            "timestamp": payload.get("timestamp"),
            "alerts": alerts,
        }
        # persist alert via repository or push to alerting queue
        try:
            await TelemetryRepository.create_alert(alert_payload)
        except Exception:
            logger.exception("Failed to persist alert")
        return alert_payload

    return None
