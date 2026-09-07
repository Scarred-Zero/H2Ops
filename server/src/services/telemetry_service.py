from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import MetricType
from src.repositories.telemetry_repo import TelemetryRepository
from src.services.websocket_manager import connection_manager


class TelemetryService:
    """
    Business logic layer sitting between API routes / MQTT subscriber and
    the repository. Owns threshold evaluation, unit handling, and the
    decision to push data over the live WebSocket channel.
    """

    ALERT_THRESHOLDS = {
        MetricType.PH: (6.5, 8.5),  # (low, high) safe band
        MetricType.TURBIDITY_NTU: (0.0, 5.0),
    }

    def __init__(self, session: AsyncSession) -> None:
        self.repo = TelemetryRepository(session)

    def _classify(self, metric_type: MetricType, value: float) -> str:
        bounds = self.ALERT_THRESHOLDS.get(metric_type)
        if not bounds:
            return "normal"
        low, high = bounds
        if value < low or value > high:
            return "alert"
        margin = (high - low) * 0.1
        if value < low + margin or value > high - margin:
            return "drift"
        return "normal"

    async def ingest_reading(
        self,
        facility_id: str,
        device_id: str,
        metric_type: MetricType,
        value: float,
        ts: datetime,
    ) -> None:
        """Called by the MQTT subscriber for every incoming telemetry point."""
        await self.repo.insert_reading(device_id, metric_type, value, ts)

        status = self._classify(metric_type, value)

        await connection_manager.broadcast_to_facility(
            facility_id,
            {
                "type": "telemetry",
                "device_id": device_id,
                "metric_type": metric_type.value,
                "value": value,
                "status": status,
                "timestamp": ts.isoformat(),
            },
        )

        if status == "alert":
            await connection_manager.broadcast_to_facility(
                facility_id,
                {
                    "type": "alert",
                    "device_id": device_id,
                    "metric_type": metric_type.value,
                    "value": value,
                    "timestamp": ts.isoformat(),
                },
            )

    async def get_chart_series(
        self,
        device_id: str,
        metric_type: MetricType,
        hours: int = 24,
        bucket_interval: str = "5 minutes",
    ) -> list[dict]:
        """Used by the analytics/dashboard REST endpoints for chart data."""
        end = datetime.utcnow()
        start = end - timedelta(hours=hours)
        return await self.repo.get_bucketed_averages(
            device_id, metric_type, start, end, bucket_interval
        )
