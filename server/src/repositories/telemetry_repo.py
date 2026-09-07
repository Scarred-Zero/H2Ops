from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import MetricType
from src.models.telemetry_log import TelemetryLog


class TelemetryRepository:
    """Data-access layer — no business logic, only persistence/query concerns."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def insert_reading(
        self, device_id: str, metric_type: MetricType, value: float, ts: datetime
    ) -> TelemetryLog:
        row = TelemetryLog(
            device_id=device_id,
            metric_type=metric_type,
            metric_value=value,
            timestamp=ts,
        )
        self.session.add(row)
        await self.session.commit()
        return row

    async def get_recent_readings(
        self, device_id: str, metric_type: MetricType, limit: int = 200
    ) -> list[TelemetryLog]:
        stmt = (
            select(TelemetryLog)
            .where(
                TelemetryLog.device_id == device_id,
                TelemetryLog.metric_type == metric_type,
            )
            .order_by(TelemetryLog.timestamp.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_bucketed_averages(
        self,
        device_id: str,
        metric_type: MetricType,
        start: datetime,
        end: datetime,
        bucket_interval: str = "5 minutes",
    ) -> list[dict]:
        """
        Uses TimescaleDB's `time_bucket` for efficient server-side
        downsampling — this is the workhorse query for dashboard charts and
        compliance-report aggregation, avoiding pulling raw high-frequency
        rows to the application layer.
        """
        query = text("""
            SELECT
                time_bucket(:bucket_interval, timestamp) AS bucket,
                avg(metric_value) AS avg_value,
                min(metric_value) AS min_value,
                max(metric_value) AS max_value,
                count(*) AS sample_count
            FROM telemetry_logs
            WHERE device_id = :device_id
              AND metric_type = :metric_type
              AND timestamp BETWEEN :start AND :end
            GROUP BY bucket
            ORDER BY bucket ASC;
            """)
        result = await self.session.execute(
            query,
            {
                "bucket_interval": bucket_interval,
                "device_id": device_id,
                "metric_type": metric_type.value,
                "start": start,
                "end": end,
            },
        )
        return [dict(row._mapping) for row in result]
