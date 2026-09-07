from datetime import datetime, timezone

from sqlalchemy import (
    Index,
    Float,
    ForeignKey,
    Enum as SAEnum,
    DateTime,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from src.models.device import DeviceType, MetricType


class TelemetryLog(Base):
    """
    TimescaleDB hypertable. `timestamp` is the partition column and is part
    of the primary key alongside device_id/metric_type, which TimescaleDB
    requires for the partitioning column to be included in any unique index.
    """

    __tablename__ = "telemetry_logs"
    __table_args__ = (Index("ix_telemetry_device_time", "device_id", "timestamp"),)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        default=lambda: datetime.now(timezone.utc),
    )
    device_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("devices.id"), primary_key=True
    )
    metric_type: Mapped[MetricType] = mapped_column(
        SAEnum(MetricType), primary_key=True
    )
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
