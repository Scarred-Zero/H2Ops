import enum

from sqlalchemy import (
    Enum as SAEnum,
    DateTime,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.models.user import User


class UserRole(str, enum.Enum):
    PLANT_OPERATOR = "plant_operator"
    FACILITY_ADMIN = "facility_admin"
    COMPLIANCE_AUDITOR = "compliance_auditor"


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole), unique=True, nullable=False
    )

    users: Mapped[list[User]] = relationship(back_populates="role")

    def __repr__(self) -> str:
        return f"<Role {self.name}>"
