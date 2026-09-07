import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch

from src.repositories.telemetry_repo import TelemetryRepository


@pytest.mark.asyncio
async def test_create_alert_publishes_to_redis_and_returns_alert(monkeypatch):
    payload = {
        "device_id": "dev-1",
        "timestamp": "2026-09-07T00:00:00Z",
        "alerts": [{"metric": "ph", "value": 9.0}],
    }

    # Mock async_session context manager and session.execute behavior
    fake_alert = AsyncMock()
    fake_alert.id = "alert-1"
    fake_alert.payload = payload

    class DummyResult:
        def __init__(self, scalar):
            self._scalar = scalar

        def scalar_one(self):
            return self._scalar

    mock_session = AsyncMock()
    mock_session.begin = AsyncMock()
    mock_session.execute = AsyncMock(return_value=DummyResult(fake_alert))
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    async def fake_async_session():
        return mock_session

    # Patch async_session and redis client
    with patch(
        "src.repositories.telemetry_repo.async_session",
        new=AsyncMock(return_value=mock_session),
    ):
        mock_redis = AsyncMock()
        mock_redis.publish = AsyncMock()
        with patch(
            "src.repositories.telemetry_repo.get_redis", return_value=mock_redis
        ):
            created = await TelemetryRepository.create_alert(payload)
            # created should be the fake_alert instance or similar
            assert created.payload == payload
            mock_redis.publish.assert_awaited()
