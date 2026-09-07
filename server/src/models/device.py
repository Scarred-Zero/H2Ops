import _uuid
from datetime import datetime, timezone

from sqlalchemy import (
    String,
    Float,
    Boolean,
    ForeignKey,
    Enum as SAEnum,
    DateTime,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.models.user import DeviceType
from src.models.facility import Facility


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    facility_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("facilities.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    device_type: Mapped[DeviceType] = mapped_column(SAEnum(DeviceType), nullable=False)
    ph_setpoint: Mapped[float] = mapped_column(Float, default=7.0)
    is_online: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # New JSONB column for dynamic thresholds
    thresholds: Mapped[dict] = mapped_column(JSONB, nullable=True, default=dict)

    facility: Mapped["Facility"] = relationship(back_populates="devices")
