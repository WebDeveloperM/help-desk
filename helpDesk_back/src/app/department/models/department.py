"""Department SQLAlchemy model."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Identity, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import BaseModel

if TYPE_CHECKING:
    from app.asset.models import Asset
    from app.ticket.models import Ticket
    from app.user.models import User


class Department(BaseModel):
    """Department model representing organizational departments."""

    __tablename__ = "departments"

    number: Mapped[int] = mapped_column(
        Integer,
        Identity(always=False),
        unique=True,
        nullable=False,
        comment="Admin-friendly sequential department number",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Department name",
    )
    name_uz: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Department name in Uzbek",
    )
    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Department code",
    )
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        comment="Parent department ID for hierarchical structure",
    )
    head_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Department head user ID",
    )
    ad_path: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Distinguished Name from Active Directory",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Whether department is active",
    )

    # Relationships
    parent: Mapped["Department | None"] = relationship(
        "Department",
        remote_side="Department.id",
        back_populates="children",
        foreign_keys=[parent_id],
    )
    children: Mapped[list["Department"]] = relationship(
        "Department",
        back_populates="parent",
        foreign_keys=[parent_id],
    )
    head_user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[head_user_id],
        back_populates="head_departments",
    )
    users: Mapped[list["User"]] = relationship(
        "User",
        foreign_keys="User.department_id",
        back_populates="department",
    )
    created_tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket",
        foreign_keys="Ticket.creator_department_id",
        back_populates="creator_department",
    )
    assigned_tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket",
        foreign_keys="Ticket.assigned_department_id",
        back_populates="assigned_department",
    )
    assets: Mapped[list["Asset"]] = relationship(
        "Asset",
        foreign_keys="Asset.department_id",
        back_populates="department",
    )

    __table_args__ = (
        Index("ix_departments_parent_id", "parent_id"),
        Index("ix_departments_code", "code"),
        Index("ix_departments_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        """String representation of department."""
        return f"<Department(id={self.id}, name={self.name}, code={self.code})>"
