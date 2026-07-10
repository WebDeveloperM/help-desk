"""Notification repository - isolated database queries."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import NotificationType, OutboxStatus
from app.notification.models import Notification, NotificationOutbox


class SQLAlchemyNotificationRepository:
    """Repository for notification database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize notification repository.

        Args:
            session: Database session.
        """
        self.session = session

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
        """
        Create a new notification (idempotent by dedup_key).

        Args:
            user_id: Recipient user ID.
            notification_type: Type of notification.
            title: Notification title.
            ticket_id: Related ticket ID.
            actor_user_id: User who triggered the event.
            body: Optional body text.
            payload_json: Optional JSON payload.
            dedup_key: Idempotency key; if already exists, returns existing row.
            expires_at: When to hard-delete; defaults to created_at + 30 days.

        Returns:
            Created or existing notification.
        """
        if dedup_key:
            existing = await self.get_by_dedup_key(dedup_key)
            if existing:
                return existing
        now = datetime.now(timezone.utc)
        if expires_at is None:
            expires_at = now + timedelta(days=30)
        notification = Notification(
            user_id=user_id,
            ticket_id=ticket_id,
            actor_user_id=actor_user_id,
            notification_type=notification_type,
            title=title,
            body=body,
            payload_json=payload_json,
            is_read=False,
            dedup_key=dedup_key or f"notif-{user_id}-{uuid4()}",
            expires_at=expires_at,
        )
        self.session.add(notification)
        await self.session.flush()
        await self.session.refresh(notification)
        return notification

    async def get_by_id(self, notification_id: UUID) -> Notification | None:
        """
        Get notification by ID.

        Args:
            notification_id: Notification UUID.

        Returns:
            Notification if found, None otherwise.
        """
        result = await self.session.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        return result.scalar_one_or_none()

    async def get_by_dedup_key(self, dedup_key: str) -> Notification | None:
        """
        Get notification by dedup key.

        Args:
            dedup_key: Idempotency key.

        Returns:
            Notification if found, None otherwise.
        """
        result = await self.session.execute(
            select(Notification).where(Notification.dedup_key == dedup_key)
        )
        return result.scalar_one_or_none()

    async def list_by_user_id(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        is_read: bool | None = None,
    ) -> tuple[list[Notification], int]:
        """
        List notifications for a user with pagination.

        Args:
            user_id: User UUID.
            skip: Number of records to skip.
            limit: Maximum number of records to return.
            is_read: Filter by read status.

        Returns:
            Tuple of (notifications list, total count).
        """
        query = select(Notification).where(
            Notification.user_id == user_id,
            Notification.expires_at > datetime.now(timezone.utc),
        )
        count_query = select(func.count()).select_from(Notification).where(
            Notification.user_id == user_id,
            Notification.expires_at > datetime.now(timezone.utc),
        )
        if is_read is not None:
            query = query.where(Notification.is_read == is_read)
            count_query = count_query.where(Notification.is_read == is_read)
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0
        query = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all()), total

    async def mark_read(self, notification_id: UUID, user_id: UUID) -> Notification | None:
        """
        Mark a notification as read (only if it belongs to user_id).

        Args:
            notification_id: Notification UUID.
            user_id: User UUID (must own the notification).

        Returns:
            Updated notification if found and owned, None otherwise.
        """
        now = datetime.now(timezone.utc)
        await self.session.execute(
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
            .values(is_read=True, read_at=now)
        )
        await self.session.flush()
        return await self.get_by_id(notification_id)

    async def mark_all_read(self, user_id: UUID) -> int:
        """
        Mark all notifications for a user as read.

        Args:
            user_id: User UUID.

        Returns:
            Number of notifications updated.
        """
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read == False,
            )
            .values(is_read=True, read_at=now)
        )
        await self.session.flush()
        return result.rowcount or 0

    async def count_unread(self, user_id: UUID) -> int:
        """
        Count unread notifications for a user (excluding expired).

        Args:
            user_id: User UUID.

        Returns:
            Unread count.
        """
        result = await self.session.execute(
            select(func.count()).select_from(Notification).where(
                Notification.user_id == user_id,
                Notification.is_read == False,
                Notification.expires_at > datetime.now(timezone.utc),
            )
        )
        return result.scalar() or 0

    async def add_outbox(
        self,
        event_type: str,
        routing_key: str,
        payload_json: dict[str, Any],
    ) -> NotificationOutbox:
        """
        Add a row to the notification outbox for at-least-once publish.

        Args:
            event_type: Event type (e.g. notification_created).
            routing_key: RabbitMQ routing key.
            payload_json: Message payload.

        Returns:
            Created outbox row.
        """
        row = NotificationOutbox(
            event_type=event_type,
            routing_key=routing_key,
            payload_json=payload_json,
            status=OutboxStatus.PENDING,
            attempts=0,
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def get_pending_outbox(
        self, limit: int = 50
    ) -> list[NotificationOutbox]:
        """
        Get outbox rows ready to publish.

        Includes:
          - PENDING rows (never attempted, or scheduled fresh).
          - FAILED rows with `next_retry_at` set and due. FAILED rows with
            `next_retry_at IS NULL` are terminal and excluded — those used to
            be retried forever.

        DEAD_LETTER rows are never returned: they are terminal and require
        human intervention (or a manual requeue migration).

        Args:
            limit: Maximum number of rows to return.

        Returns:
            List of outbox rows.
        """
        now = datetime.now(timezone.utc)
        ready = or_(
            NotificationOutbox.status == OutboxStatus.PENDING,
            and_(
                NotificationOutbox.status == OutboxStatus.FAILED,
                NotificationOutbox.next_retry_at.is_not(None),
                NotificationOutbox.next_retry_at <= now,
            ),
        )
        result = await self.session.execute(
            select(NotificationOutbox)
            .where(ready)
            .order_by(NotificationOutbox.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_outbox_sent(
        self, outbox_id: UUID, published_at: datetime
    ) -> None:
        """
        Mark an outbox row as sent.

        Args:
            outbox_id: Outbox row UUID.
            published_at: When the message was published.
        """
        await self.session.execute(
            update(NotificationOutbox)
            .where(NotificationOutbox.id == outbox_id)
            .values(
                status=OutboxStatus.SENT,
                published_at=published_at,
            )
        )
        await self.session.flush()

    async def mark_outbox_failed(
        self,
        outbox_id: UUID,
        attempts: int,
        next_retry_at: datetime,
        last_error: str,
    ) -> None:
        """
        Mark an outbox row as transiently failed and schedule the next retry.

        For terminal failures (max attempts exhausted) call
        `mark_outbox_dead_letter` instead.

        Args:
            outbox_id: Outbox row UUID.
            attempts: New attempt count.
            next_retry_at: When to retry. Required — terminal failures use
                `mark_outbox_dead_letter`, not this method.
            last_error: Error message.
        """
        await self.session.execute(
            update(NotificationOutbox)
            .where(NotificationOutbox.id == outbox_id)
            .values(
                status=OutboxStatus.FAILED,
                attempts=attempts,
                next_retry_at=next_retry_at,
                last_error=last_error,
            )
        )
        await self.session.flush()

    async def mark_outbox_dead_letter(
        self,
        outbox_id: UUID,
        attempts: int,
        last_error: str,
    ) -> None:
        """
        Mark an outbox row as dead-lettered (retry budget exhausted).

        Sets `next_retry_at` to NULL so the row is never picked up by
        `get_pending_outbox`. Requires human intervention or a manual requeue
        to reprocess.

        Args:
            outbox_id: Outbox row UUID.
            attempts: Final attempt count.
            last_error: Last error message that caused the dead-letter.
        """
        await self.session.execute(
            update(NotificationOutbox)
            .where(NotificationOutbox.id == outbox_id)
            .values(
                status=OutboxStatus.DEAD_LETTER,
                attempts=attempts,
                next_retry_at=None,
                last_error=last_error,
            )
        )
        await self.session.flush()
