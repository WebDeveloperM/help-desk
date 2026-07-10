"""Asset SQLAlchemy model."""

from datetime import datetime

from typing import TYPE_CHECKING
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import BaseModel
from app.core.enums import AssetLifecycleStatus

if TYPE_CHECKING:
    from app.department.models import Department
    from app.ticket.models import Ticket
    from app.user.models import User


class Asset(BaseModel):
    """Asset model representing a managed company asset."""

    __tablename__ = "assets"

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Asset name",
    )
    asset_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Asset type (printer, laptop, etc.)",
    )
    inventory_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique inventory number",
    )
    serial_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Vendor serial number",
    )
    department_id: Mapped[UUID] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Owner department",
    )
    assigned_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Current asset owner user",
    )
    status: Mapped[AssetLifecycleStatus] = mapped_column(
        PG_ENUM(
            AssetLifecycleStatus,
            name="asset_lifecycle_status",
            create_type=False,
            values_callable=lambda e: [member.value for member in e],
        ),
        nullable=False,
        default=AssetLifecycleStatus.ACTIVE,
        index=True,
        comment="Lifecycle status",
    )
    location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Asset location",
    )
    purchase_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Purchase date",
    )
    warranty_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Warranty expiration date",
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Additional notes",
    )
    image_urls: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Image URLs stored in MinIO",
    )
    embedding: Mapped[list[float]] = mapped_column(
        Vector(16),
        nullable=False,
        comment="Search embedding vector",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Soft-delete flag",
    )

    department: Mapped["Department"] = relationship(
        "Department",
        foreign_keys=[department_id],
        back_populates="assets",
    )
    assigned_user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[assigned_user_id],
        back_populates="owned_assets",
    )
    tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket",
        secondary="ticket_assets",
        back_populates="assets",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_assets_name", "name"),
    )

    def __repr__(self) -> str:
        """String representation of asset."""
        return (
            f"<Asset(id={self.id}, inventory_number={self.inventory_number}, "
            f"status={self.status.value}, is_active={self.is_active})>"
        )
