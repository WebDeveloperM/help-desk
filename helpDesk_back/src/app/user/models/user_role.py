"""UserRole SQLAlchemy model.

User roles are currently disabled: no sync from Keycloak to DB.
Model matches migration 002 (composite PK). Auth uses Keycloak token roles only.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import Role

if TYPE_CHECKING:
    from app.department.models import Department
    from app.user.models import User


class UserRole(Base):
    """UserRole model (table exists from 002; role sync disabled)."""

    __tablename__ = "user_roles"
    __abstract__ = False

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
        comment="User ID",
    )
    role: Mapped[Role] = mapped_column(
        PG_ENUM(
            Role,
            name="role",
            create_type=False,
            values_callable=lambda e: [member.value for member in e],
        ),
        nullable=False,
        primary_key=True,
        comment="User role",
    )
    department_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=True,
        primary_key=True,
        comment="Department ID where role applies",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="roles",
        foreign_keys=[user_id],
    )
    department: Mapped["Department | None"] = relationship(
        "Department",
        foreign_keys=[department_id],
    )

    __table_args__ = (
        UniqueConstraint("user_id", "role", "department_id", name="uq_user_roles"),
        Index("ix_user_roles_user_id", "user_id"),
        Index("ix_user_roles_role", "role"),
        Index("ix_user_roles_department_id", "department_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<UserRole(user_id={self.user_id}, role={self.role.value}, "
            f"department_id={self.department_id})>"
        )
