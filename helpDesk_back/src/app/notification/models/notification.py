"""Notification SQLAlchemy model."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import BaseModel
from app.core.enums import NotificationType

if TYPE_CHECKING:
    from app.ticket.models import Ticket
    from app.user.models import User


class Notification(BaseModel):
    """In-app notification for a user."""

    __tablename__ = "notifications"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Recipient user ID",
    )
    ticket_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Related ticket ID",
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who triggered the event",
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        PG_ENUM(
            NotificationType,
            name="notification_type",
            create_type=False,
            values_callable=lambda e: [member.value for member in e],
        ),
        nullable=False,
        index=True,
        comment="Notification type",
    )
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Notification title",
    )
    body: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Notification body",
    )
    payload_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Additional payload (e.g. ticket_number, status)",
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether the user has read the notification",
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the notification was read",
    )
    dedup_key: Mapped[str] = mapped_column(
        String(512),
        unique=True,
        nullable=False,
        index=True,
        comment="Idempotency key for at-least-once delivery",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="When to hard-delete (created_at + retention)",
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
    )
    ticket: Mapped["Ticket | None"] = relationship(
        "Ticket",
        foreign_keys=[ticket_id],
    )
    actor: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[actor_user_id],
    )

    __table_args__ = (
        UniqueConstraint("dedup_key", name="uq_notifications_dedup_key"),
        Index("ix_notifications_user_id_is_read_created_at", "user_id", "is_read", "created_at"),
        Index("ix_notifications_user_id_created_at", "user_id", "created_at"),
        Index("ix_notifications_expires_at", "expires_at"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<Notification(id={self.id}, user_id={self.user_id}, "
            f"type={self.notification_type.value}, is_read={self.is_read})>"
        )
