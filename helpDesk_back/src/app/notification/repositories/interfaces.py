"""Notification repository abstraction."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from app.core.enums import NotificationType
from app.notification.models import Notification, NotificationOutbox


class NotificationRepository(Protocol):
    """Repository interface for notification persistence operations."""

    async def create(
        self,
        user_id: UUID,
        notification_type: NotificationType,
        title: str,
        ticket_id: UUID | None = None,
        actor_user_id: UUID | None = None,
        body: str | None = None,
        payload_json: dict[str, Any] | None = None,
        dedup_key: str | None = None,
        expires_at: datetime | None = None,
    ) -> Notification:
        """Persist a new notification."""

    async def get_by_id(self, notification_id: UUID) -> Notification | None:
        """Return a notification by ID."""

    async def get_by_dedup_key(self, dedup_key: str) -> Notification | None:
        """Return a notification by dedup key."""

    async def list_by_user_id(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        is_read: bool | None = None,
    ) -> tuple[list[Notification], int]:
        """Return paginated notifications for a user with total count."""

    async def mark_read(self, notification_id: UUID, user_id: UUID) -> Notification | None:
        """Mark one notification as read for a user."""

    async def mark_all_read(self, user_id: UUID) -> int:
        """Mark all notifications as read for user."""

    async def count_unread(self, user_id: UUID) -> int:
        """Return unread notification count for user."""

    async def add_outbox(
        self,
        event_type: str,
        routing_key: str,
        payload_json: dict[str, Any],
    ) -> NotificationOutbox:
        """Persist outbox event row."""

    async def get_pending_outbox(self, limit: int = 50) -> list[NotificationOutbox]:
        """Return pending outbox rows ready for publish."""

    async def mark_outbox_sent(self, outbox_id: UUID, published_at: datetime) -> None:
        """Mark outbox row as sent."""

    async def mark_outbox_failed(
        self,
        outbox_id: UUID,
        attempts: int,
        next_retry_at: datetime | None,
        last_error: str,
    ) -> None:
        """Mark outbox row as failed with retry metadata."""
