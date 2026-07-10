"""Notification outbox SQLAlchemy model for transactional outbox pattern."""

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import BaseModel
from app.core.enums import OutboxStatus


class NotificationOutbox(BaseModel):
    """Outbox row for at-least-once publish to RabbitMQ."""

    __tablename__ = "notification_outbox"

    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Event type (e.g. notification_created)",
    )
    routing_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="RabbitMQ routing key",
    )
    payload_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="Message payload",
    )
    status: Mapped[OutboxStatus] = mapped_column(
        PG_ENUM(
            OutboxStatus,
            name="outbox_status",
            create_type=False,
            values_callable=lambda e: [member.value for member in e],
        ),
        nullable=False,
        default=OutboxStatus.PENDING,
        index=True,
        comment="Delivery status",
    )
    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of publish attempts",
    )
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Next retry time for failed publishes",
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When successfully published",
    )
    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Last error message if failed",
    )

    __table_args__ = (
        Index("ix_notification_outbox_status_next_retry_at", "status", "next_retry_at"),
        Index("ix_notification_outbox_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<NotificationOutbox(id={self.id}, event_type={self.event_type}, "
            f"status={self.status.value}, attempts={self.attempts})>"
        )
