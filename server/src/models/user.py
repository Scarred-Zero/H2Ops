import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    String,
    Float,
    Boolean,
    ForeignKey,
    Enum as SAEnum,
    DateTime,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.models.facility import Facility


def _uuid() -> str:
    return str(uuid.uuid4())


class UserRole(str, enum.Enum):
    PLANT_OPERATOR = "plant_operator"
    FACILITY_ADMIN = "facility_admin"
    COMPLIANCE_AUDITOR = "compliance_auditor"


class DeviceType(str, enum.Enum):
    PH_SENSOR = "ph_sensor"
    TURBIDITY_SENSOR = "turbidity_sensor"
    DOSING_PUMP = "dosing_pump"
    FLOW_METER = "flow_meter"


class MetricType(str, enum.Enum):
    PH = "ph"
    TURBIDITY_NTU = "turbidity_ntu"
    CHLORINE_DOSE_ML = "chlorine_dose_ml"
    FLOW_RATE = "flow_rate"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), nullable=False)
    facility_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("facilities.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    facility: Mapped["Facility | None"] = relationship(back_populates="users")

