# server/tests/test_devices_router.py
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from src.main import app  # ensure server/main.py exposes `app`


@pytest.mark.asyncio
async def test_create_device_endpoint(monkeypatch):
    payload = {
        "facility_id": "fac-1",
        "name": "Test Device",
        "device_type": "SENSOR",
        "ph_setpoint": 7.2,
        "thresholds": {"ph_min": 6.5, "ph_max": 8.5},
    }

    # Mock DB insert/returning behavior
    fake_device = AsyncMock()
    fake_device.id = "dev-1"
    fake_device.facility_id = payload["facility_id"]
    fake_device.name = payload["name"]
    fake_device.device_type = payload["device_type"]
    fake_device.ph_setpoint = payload["ph_setpoint"]
    fake_device.is_online = True
    fake_device.thresholds = payload["thresholds"]

    # Patch async_session to return a session whose execute returns the fake device
    mock_session = AsyncMock()

    class DummyResult:
        def __init__(self, scalar):
            self._scalar = scalar

        def scalar_one(self):
            return self._scalar

    mock_session.execute = AsyncMock(return_value=DummyResult(fake_device))
    mock_session.begin = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "src.api.v1.routes.devices.async_session",
        new=AsyncMock(return_value=mock_session),
    ):
        async with AsyncClient(app=app, base_url="http://testserver") as client:
            resp = await client.post("/api/v1/devices/", json=payload)
            assert resp.status_code == 201
            body = resp.json()
            assert body["name"] == payload["name"]
            assert body["thresholds"]["ph_min"] == 6.5
